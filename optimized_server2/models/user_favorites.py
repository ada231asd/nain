"""
Модель для работы с избранными станциями пользователей
"""
from typing import Optional, List
from datetime import datetime
import aiomysql


class UserFavorites:
    """Модель избранных станций пользователя"""
    
    def __init__(self, id: int, user_id: int, station_id: int, 
                 created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.station_id = station_id
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'station_id': self.station_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int) -> List['UserFavorites']:
        """Получает избранные станции пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, user_id, station_id, created_at
                    FROM user_favorites
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                rows = await cur.fetchall()
                
                favorites = []
                for row in rows:
                    favorites.append(cls(
                        id=row[0],
                        user_id=row[1],
                        station_id=row[2],
                        created_at=row[3]
                    ))
                return favorites
    
    @classmethod
    async def add_favorite(cls, db_pool, user_id: int, station_id: int) -> 'UserFavorites':
        """Добавляет станцию в избранное"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Проверяем, не добавлена ли уже станция
                await cur.execute("""
                    SELECT id FROM user_favorites 
                    WHERE user_id = %s AND station_id = %s
                """, (user_id, station_id))
                existing = await cur.fetchone()
                
                if existing:
                    raise ValueError("Станция уже в избранном")
                
                await cur.execute("""
                    INSERT INTO user_favorites (user_id, station_id, created_at)
                    VALUES (%s, %s, %s)
                """, (user_id, station_id, datetime.now()))
                
                favorite_id = cur.lastrowid
                
                return cls(
                    id=favorite_id,
                    user_id=user_id,
                    station_id=station_id,
                    created_at=datetime.now()
                )
    
    @classmethod
    async def remove_favorite(cls, db_pool, user_id: int, station_id: int) -> bool:
        """Удаляет станцию из избранного"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    DELETE FROM user_favorites 
                    WHERE user_id = %s AND station_id = %s
                """, (user_id, station_id))
                
                return cur.rowcount > 0
