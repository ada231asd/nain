"""
Модель для работы с типами ошибок повербанков
"""
from typing import Optional, List
import aiomysql


class PowerbankError:
    """Модель типа ошибки повербанка"""
    
    def __init__(self, id_er: int, type_error: str):
        self.id_er = id_er
        self.type_error = type_error
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'id_er': self.id_er,
            'type_error': self.type_error
        }
    
    @classmethod
    async def get_all(cls, db_pool) -> List['PowerbankError']:
        """Получает все типы ошибок"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id_er, type_error FROM powerbank_error ORDER BY id_er"
                )
                rows = await cur.fetchall()
        
        return [
            cls(id_er=row[0], type_error=row[1])
            for row in rows
        ]
    
    @classmethod
    async def get_by_id(cls, db_pool, id_er: int) -> Optional['PowerbankError']:
        """Получает тип ошибки по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id_er, type_error FROM powerbank_error WHERE id_er = %s",
                    (id_er,)
                )
                row = await cur.fetchone()
        
        if not row:
            return None
        
        return cls(id_er=row[0], type_error=row[1])
