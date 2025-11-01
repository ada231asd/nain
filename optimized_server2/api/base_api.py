"""
Базовый класс для всех API с общей логикой
"""
from aiohttp.web import Request, Response
from aiohttp import web
import aiomysql
from typing import Optional, Dict, Any
from utils.soft_delete import (
    soft_delete_user, soft_delete_station, soft_delete_powerbank,
    soft_delete_org_unit, soft_delete_order, SoftDeleteMixin
)
from utils.centralized_logger import get_logger


logger = get_logger('base_api')


class BaseAPI:
    """Базовый класс для всех API с общими методами"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # ============ Проверка авторизации и прав ============
    
    def get_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Получить пользователя из request"""
        try:
            return request['user'] if 'user' in request else None
        except (KeyError, TypeError):
            return None
    
    def check_auth(self, request: Request) -> tuple[bool, Optional[Response]]:
        """
        Проверить авторизацию
        """
        user = self.get_user_from_request(request)
        if not user:
            return False, web.json_response({
                'error': 'Требуется авторизация'
            }, status=401)
        return True, None
    
    async def check_admin_permissions(self, user_id: int) -> bool:
        """Проверка прав администратора (любого уровня)"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT role FROM user_role 
                    WHERE user_id = %s 
                    AND role IN ('service_admin', 'group_admin', 'subgroup_admin')
                """, (user_id,))
                roles = await cur.fetchall()
                return len(roles) > 0
    
    async def check_service_admin(self, user_id: int) -> bool:
        """Проверка прав service_admin"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT role FROM user_role 
                    WHERE user_id = %s AND role = 'service_admin'
                """, (user_id,))
                return await cur.fetchone() is not None
    
    async def check_group_admin(self, user_id: int, org_unit_id: Optional[int] = None) -> bool:
        """Проверка прав group_admin для конкретной группы или любой"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                if org_unit_id:
                    await cur.execute("""
                        SELECT role FROM user_role 
                        WHERE user_id = %s 
                        AND role IN ('service_admin', 'group_admin')
                        AND (org_unit_id = %s OR role = 'service_admin')
                    """, (user_id, org_unit_id))
                else:
                    await cur.execute("""
                        SELECT role FROM user_role 
                        WHERE user_id = %s 
                        AND role IN ('service_admin', 'group_admin')
                    """, (user_id,))
                return await cur.fetchone() is not None
    
    def check_required_fields(self, data: dict, required_fields: list) -> tuple[bool, Optional[Response]]:
        """
        Проверить наличие обязательных полей
        """
        for field in required_fields:
            if field not in data:
                return False, web.json_response({
                    'error': f'Отсутствует обязательное поле: {field}'
                }, status=400)
        return True, None
    
    # ============ Мягкое удаление ============
    
    async def soft_delete_entity(self, entity_type: str, entity_id: int, user_id: Optional[int] = None) -> tuple[bool, str]:
        """
        Универсальное мягкое удаление сущности
        """
        delete_functions = {
            'user': lambda db, id: soft_delete_user(db, id),
            'station': lambda db, id: soft_delete_station(db, id),
            'powerbank': lambda db, id: soft_delete_powerbank(db, id),
            'org_unit': lambda db, id: soft_delete_org_unit(db, id),
            'order': lambda db, id: soft_delete_order(db, id)
        }
        
        if entity_type not in delete_functions:
            table_mapping = {}
            
            if entity_type in table_mapping:
                table, id_field = table_mapping[entity_type]
                success = await SoftDeleteMixin.soft_delete(self.db_pool, table, entity_id, id_field)
            else:
                return False, f'Неподдерживаемый тип сущности: {entity_type}'
        else:
            success = await delete_functions[entity_type](self.db_pool, entity_id)
        
        if success:
            return True, f'{entity_type} #{entity_id} успешно удален'
        else:
            return False, f'{entity_type} #{entity_id} не найден или уже удален'
    
    # ============ Валидация ============
    
    def validate_enum(self, value: str, valid_values: list, field_name: str) -> tuple[bool, Optional[Response]]:
        """Проверка значения enum"""
        if value not in valid_values:
            return False, web.json_response({
                'error': f'Недопустимое значение для {field_name}. Допустимые значения: {", ".join(valid_values)}'
            }, status=400)
        return True, None
    
    # ============ Получение данных ============
    
    async def get_entity_by_id(self, table: str, id_field: str, entity_id: int, 
                                include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Получить сущность по ID
        """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                where_clause = f"{id_field} = %s"
                if not include_deleted:
                    # Для powerbank используем power_er != 5, для остальных - is_deleted = 0
                    if table == 'powerbank':
                        where_clause += " AND (power_er != 5 OR power_er IS NULL) AND status != 'system_error'"
                    else:
                        where_clause += " AND is_deleted = 0"
                
                query = f"SELECT * FROM {table} WHERE {where_clause}"
                await cur.execute(query, (entity_id,))
                return await cur.fetchone()
    
    async def entity_exists(self, table: str, id_field: str, entity_id: int, 
                            include_deleted: bool = False) -> bool:
        """Проверить существование сущности"""
        entity = await self.get_entity_by_id(table, id_field, entity_id, include_deleted)
        return entity is not None
    
    # ============ Обработка ошибок ============
    
    def error_response(self, message: str, status: int = 500) -> Response:
        """Стандартный ответ с ошибкой"""
        logger.error(f"API Error: {message}")
        return web.json_response({
            'success': False,
            'error': message
        }, status=status)
    
    def success_response(self, data: Any = None, message: str = None) -> Response:
        """Стандартный успешный ответ"""
        response = {'success': True}
        if message:
            response['message'] = message
        if data is not None:
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data
        return web.json_response(response)
    
    # ============ Фильтрация удаленных данных ============
    
    async def should_show_deleted(self, request: Request) -> bool:
        """
        Проверяет, нужно ли показывать удаленные записи
        """
        # Проверяем роль
        user = self.get_user_from_request(request)
        if not user:
            return False
        
        user_id = user.get('user_id')
        if not user_id:
            return False
        
        # Проверяем является ли пользователь service_admin
        is_service_admin = await self.check_service_admin(user_id)
        
        if not is_service_admin:
            return False
        
        show_deleted = request.query.get('show_deleted', 'true').lower()
        
        return show_deleted != 'false'
    
    def add_is_deleted_filter(
        self, 
        where_conditions: list, 
        table_aliases: list, 
        show_deleted: bool = False,
        table_name: str = None
    ):
        """
        Добавляет фильтр is_deleted = 0 для указанных таблиц

        """
        if not show_deleted:
            for alias in table_aliases:
                if table_name == 'powerbank' or (table_name is None and 'p' in table_aliases and len(table_aliases) == 1):
                    where_conditions.append(f"({alias}.power_er != 5 OR {alias}.power_er IS NULL) AND {alias}.status != 'system_error'")
                else:
                    where_conditions.append(f"{alias}.is_deleted = 0")
    
    # ============ Валидация ID ============
    
    def parse_int_param(self, value: str, param_name: str) -> tuple[Optional[int], Optional[Response]]:
        """
        Парсинг целочисленного параметра
        """
        try:
            return int(value), None
        except ValueError:
            return None, self.error_response(f'Некорректное значение {param_name}', 400)

