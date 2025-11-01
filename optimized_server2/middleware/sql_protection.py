"""
Защита от SQL инъекций
"""
import re
from typing import Any, Dict, List, Optional, Union
import aiomysql
from aiohttp import web
from contextlib import asynccontextmanager


class SQLProtection:
    """Класс для защиты от SQL инъекций"""
    
    def __init__(self):
        # Паттерны SQL инъекций
        self.sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'or\s+1\s*=\s*1',
            r'\'\s*or\s*\'\w*\'\s*=\s*\'\w*\'',
            r'\'\s*or\s*1\s*=\s*1',
            r'\'\s*;\s*--',
            r'\'\s*;\s*drop',
            r'\'\s*;\s*insert',
            r'\'\s*;\s*update',
            r'\'\s*;\s*delete',
            r'exec\s*\(',
            r'execute\s*\(',
            r'sp_',
            r'xp_',
            r'waitfor\s+delay',
            r'benchmark\s*\(',
            r'sleep\s*\(',
            r'load_file\s*\(',
            r'into\s+outfile',
            r'into\s+dumpfile'
        ]
        
        # Компилируем паттерны для быстрой проверки
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns]
    
    def check_sql_injection(self, value: Any) -> bool:
        """Проверяет значение на SQL инъекции"""
        if value is None:
            return False
        
        str_value = str(value).lower()
        
        for pattern in self.compiled_patterns:
            if pattern.search(str_value):
                return True
        
        return False
    
    def sanitize_parameter(self, value: Any) -> str:
        """Очищает параметр от потенциально опасных символов"""
        if value is None:
            return None
        
        str_value = str(value)
        
        # Удаляем потенциально опасные символы
        dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute']
        for char in dangerous_chars:
            str_value = str_value.replace(char, '')
        
        # Ограничиваем длину
        if len(str_value) > 1000:
            str_value = str_value[:1000]
        
        return str_value.strip()
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Валидирует параметры на SQL инъекции"""
        errors = []
        sanitized_params = {}
        
        for key, value in params.items():
            if self.check_sql_injection(key):
                errors.append(f'Подозрительный ключ параметра: {key}')
                continue
            
            if self.check_sql_injection(value):
                errors.append(f'Подозрительное значение параметра {key}: {value}')
                continue
            
            sanitized_params[key] = self.sanitize_parameter(value)
        
        return {
            'sanitized_params': sanitized_params,
            'errors': errors
        }


class SecureDatabase:
    """Безопасный интерфейс для работы с базой данных"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.sql_protection = SQLProtection()
    
    @asynccontextmanager
    async def get_connection(self):
        """Получает безопасное соединение с БД"""
        async with self.db_pool.acquire() as conn:
            yield conn
    
    async def execute_safe_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Выполняет безопасный запрос"""
        # Проверяем запрос на SQL инъекции
        if self.sql_protection.check_sql_injection(query):
            raise ValueError("Обнаружена попытка SQL инъекции в запросе")
        
        # Проверяем параметры
        if params:
            for param in params:
                if self.sql_protection.check_sql_injection(param):
                    raise ValueError("Обнаружена попытка SQL инъекции в параметрах")
        
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                return await cur.fetchall()
    
    async def execute_safe_update(self, query: str, params: tuple = None) -> int:
        """Выполняет безопасное обновление"""
        # Проверяем запрос на SQL инъекции
        if self.sql_protection.check_sql_injection(query):
            raise ValueError("Обнаружена попытка SQL инъекции в запросе")
        
        # Проверяем параметры
        if params:
            for param in params:
                if self.sql_protection.check_sql_injection(param):
                    raise ValueError("Обнаружена попытка SQL инъекции в параметрах")
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.rowcount
    
    async def execute_safe_insert(self, query: str, params: tuple = None) -> int:
        """Выполняет безопасную вставку"""
        # Проверяем запрос на SQL инъекции
        if self.sql_protection.check_sql_injection(query):
            raise ValueError("Обнаружена попытка SQL инъекции в запросе")
        
        # Проверяем параметры
        if params:
            for param in params:
                if self.sql_protection.check_sql_injection(param):
                    raise ValueError("Обнаружена попытка SQL инъекции в параметрах")
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.lastrowid
    
    async def execute_safe_delete(self, query: str, params: tuple = None) -> int:
        """Выполняет безопасное удаление"""
        # Проверяем запрос на SQL инъекции
        if self.sql_protection.check_sql_injection(query):
            raise ValueError("Обнаружена попытка SQL инъекции в запросе")
        
        # Проверяем параметры
        if params:
            for param in params:
                if self.sql_protection.check_sql_injection(param):
                    raise ValueError("Обнаружена попытка SQL инъекции в параметрах")
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.rowcount


def create_secure_database(db_pool):
    """Создает экземпляр безопасной базы данных"""
    return SecureDatabase(db_pool)


@web.middleware
async def sql_protection_middleware(request, handler):
    """Middleware для проверки параметров запроса на SQL инъекции"""
    # Проверяем query параметры
    if request.query_string:
        sql_protection = SQLProtection()
        for key, value in request.query.items():
            if sql_protection.check_sql_injection(key) or sql_protection.check_sql_injection(value):
                return web.json_response({'error': 'Обнаружена попытка SQL инъекции'}, status=400)
    
    return await handler(request)


class SQLProtectionMiddleware:
    """Класс middleware для защиты от SQL инъекций"""
    
    def __init__(self):
        self.sql_protection = SQLProtection()
    
    async def __call__(self, request, handler):
        """Вызов middleware"""
        return await sql_protection_middleware(request, handler)
