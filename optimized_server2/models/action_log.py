"""
Модель для работы с логами действий
"""
from typing import Optional, List
from datetime import datetime
import aiomysql


class ActionLog:
    """Модель лога действия"""
    
    def __init__(self, id: int, user_id: Optional[int], action_type: str,
                 entity_type: Optional[str], entity_id: Optional[int],
                 description: Optional[str], ip_address: Optional[str],
                 user_agent: Optional[str], created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.action_type = action_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.description = description
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    async def create(cls, db_pool, user_id: Optional[int], action_type: str,
                    entity_type: Optional[str], entity_id: Optional[int],
                    description: Optional[str], ip_address: Optional[str] = None,
                    user_agent: Optional[str] = None) -> 'ActionLog':
        """Создает лог действия"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                now = datetime.now()
                await cur.execute("""
                    INSERT INTO action_logs (user_id, action_type, entity_type, entity_id, description, ip_address, user_agent, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, action_type, entity_type, entity_id, description, ip_address, user_agent, now))
                
                log_id = cur.lastrowid
                
                return cls(
                    id=log_id,
                    user_id=user_id,
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    description=description,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    created_at=now
                )
    
    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int, limit: int = 100) -> List['ActionLog']:
        """Получает логи пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, user_id, action_type, entity_type, entity_id, description, ip_address, user_agent, created_at
                    FROM action_logs
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                rows = await cur.fetchall()
                
                logs = []
                for row in rows:
                    logs.append(cls(
                        id=row[0],
                        user_id=row[1],
                        action_type=row[2],
                        entity_type=row[3],
                        entity_id=row[4],
                        description=row[5],
                        ip_address=row[6],
                        user_agent=row[7],
                        created_at=row[8]
                    ))
                return logs
