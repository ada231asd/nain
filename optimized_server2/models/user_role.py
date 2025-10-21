"""
Модель для работы с ролями пользователей
"""
from typing import Optional, List
from datetime import datetime
import aiomysql


class UserRole:
    """Модель роли пользователя"""
    
    def __init__(self, id: int, user_id: int, org_unit_id: Optional[int], 
                 role: str, created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.org_unit_id = org_unit_id
        self.role = role
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'org_unit_id': self.org_unit_id,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    async def get_primary_role(cls, db_pool, user_id: int) -> Optional['UserRole']:
        """Возвращает основную роль пользователя."""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, user_id, org_unit_id, role, created_at
                    FROM user_role
                    WHERE user_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                """, (user_id,))
                row = await cur.fetchone()
                if not row:
                    return None
                return cls(
                    id=row[0],
                    user_id=row[1],
                    org_unit_id=row[2],
                    role=row[3],
                    created_at=row[4]
                )
    
    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int) -> List['UserRole']:
        """Получает роли пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, user_id, org_unit_id, role, created_at
                    FROM user_role
                    WHERE user_id = %s
                """, (user_id,))
                rows = await cur.fetchall()
                
                roles = []
                for row in rows:
                    roles.append(cls(
                        id=row[0],
                        user_id=row[1],
                        org_unit_id=row[2],
                        role=row[3],
                        created_at=row[4]
                    ))
                return roles
    
    @classmethod
    async def create(cls, db_pool, user_id: int, org_unit_id: Optional[int], 
                    role: str) -> 'UserRole':
        """Создает роль пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO user_role (user_id, org_unit_id, role, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, org_unit_id, role, datetime.now()))
                
                role_id = cur.lastrowid
                
                return cls(
                    id=role_id,
                    user_id=user_id,
                    org_unit_id=org_unit_id,
                    role=role,
                    created_at=datetime.now()
                )