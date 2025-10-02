"""
Модель для работы с ролями пользователей
"""
from typing import Optional, List
import aiomysql
from utils.time_utils import get_moscow_time


class UserRole:
    """Модель роли пользователя"""
    
    def __init__(self, id: int, user_id: int, org_unit_id: Optional[int], 
                 role: str, created_at: Optional[str] = None):
        self.id = id
        self.user_id = user_id
        self.org_unit_id = org_unit_id
        self.role = role
        self.created_at = created_at
    
    @classmethod
    async def get_primary_role(cls, db_pool, user_id: int) -> Optional['UserRole']:
        """
        Получает основную роль пользователя
        
        Приоритет ролей (от высшего к низшему):
        1. service_admin (глобальный администратор)
        2. group_admin (администратор группы)
        3. subgroup_admin (администратор подгруппы)
        4. user (обычный пользователь)
        """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Получаем все роли пользователя, отсортированные по приоритету
                await cur.execute("""
                    SELECT id, user_id, org_unit_id, role, created_at
                    FROM user_role 
                    WHERE user_id = %s
                    ORDER BY 
                        CASE role
                            WHEN 'service_admin' THEN 1
                            WHEN 'group_admin' THEN 2
                            WHEN 'subgroup_admin' THEN 3
                            WHEN 'user' THEN 4
                            ELSE 5
                        END
                    LIMIT 1
                """, (user_id,))
                
                result = await cur.fetchone()
                if result:
                    return cls(*result)
                return None
    
    @classmethod
    async def get_all_user_roles(cls, db_pool, user_id: int) -> List['UserRole']:
        """Получает все роли пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, user_id, org_unit_id, role, created_at
                    FROM user_role 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                
                results = await cur.fetchall()
                return [cls(*result) for result in results]
    
    @classmethod
    async def has_role(cls, db_pool, user_id: int, role: str, org_unit_id: Optional[int] = None) -> bool:
        """
        Проверяет, есть ли у пользователя указанная роль
        
        Args:
            db_pool: Пул соединений с БД
            user_id: ID пользователя
            role: Название роли
            org_unit_id: ID организационной единицы (опционально)
        """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                if org_unit_id is not None:
                    await cur.execute("""
                        SELECT COUNT(*) FROM user_role 
                        WHERE user_id = %s AND role = %s AND org_unit_id = %s
                    """, (user_id, role, org_unit_id))
                else:
                    await cur.execute("""
                        SELECT COUNT(*) FROM user_role 
                        WHERE user_id = %s AND role = %s
                    """, (user_id, role))
                
                result = await cur.fetchone()
                return result[0] > 0
    
    @classmethod
    async def is_service_admin(cls, db_pool, user_id: int) -> bool:
        """Проверяет, является ли пользователь глобальным администратором"""
        return await cls.has_role(db_pool, user_id, 'service_admin')
    
    @classmethod
    async def is_group_admin(cls, db_pool, user_id: int, org_unit_id: Optional[int] = None) -> bool:
        """Проверяет, является ли пользователь администратором группы"""
        if org_unit_id is not None:
            return await cls.has_role(db_pool, user_id, 'group_admin', org_unit_id)
        else:
            return await cls.has_role(db_pool, user_id, 'group_admin')
    
    @classmethod
    async def is_subgroup_admin(cls, db_pool, user_id: int, org_unit_id: Optional[int] = None) -> bool:
        """Проверяет, является ли пользователь администратором подгруппы"""
        if org_unit_id is not None:
            return await cls.has_role(db_pool, user_id, 'subgroup_admin', org_unit_id)
        else:
            return await cls.has_role(db_pool, user_id, 'subgroup_admin')
    
    @classmethod
    async def get_user_org_units(cls, db_pool, user_id: int) -> List[int]:
        """
        Получает список всех организационных единиц, к которым привязан пользователь
        """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT DISTINCT org_unit_id 
                    FROM user_role 
                    WHERE user_id = %s AND org_unit_id IS NOT NULL
                """, (user_id,))
                
                results = await cur.fetchall()
                return [result[0] for result in results]
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'org_unit_id': self.org_unit_id,
            'role': self.role,
            'created_at': self.created_at
        }
    
    def get_role_description(self) -> str:
        """Возвращает описание роли"""
        descriptions = {
            'service_admin': 'Глобальный администратор',
            'group_admin': 'Администратор группы',
            'subgroup_admin': 'Администратор подгруппы',
            'user': 'Обычный пользователь'
        }
        return descriptions.get(self.role, 'Неизвестная роль')
    
    def can_access_org_unit(self, target_org_unit_id: int) -> bool:
        """
        Проверяет, может ли пользователь с данной ролью получить доступ к указанной org_unit
        Базовая проверка без учета иерархии (для этого используйте функции в org_unit_utils)
        """
        if self.role == 'service_admin':
            return True  # Глобальный админ может всё
        
        if self.org_unit_id is None:
            return False  # Роль без привязки к org_unit не может получить доступ
        
        return self.org_unit_id == target_org_unit_id
