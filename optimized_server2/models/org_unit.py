"""
Модель для работы с организационными единицами
"""
from typing import Optional
import aiomysql


class OrgUnit:
    """Модель организационной единицы"""
    
    def __init__(self, org_unit_id: int, parent_org_unit_id: Optional[int], 
                 unit_type: str, name: str):
        self.org_unit_id = org_unit_id
        self.parent_org_unit_id = parent_org_unit_id
        self.unit_type = unit_type
        self.name = name
    
    @classmethod
    async def get_by_id(cls, db_pool, org_unit_id: int) -> Optional['OrgUnit']:
        """Получает организационную единицу по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT org_unit_id, parent_org_unit_id, unit_type, name
                    FROM org_unit
                    WHERE org_unit_id = %s
                """, (org_unit_id,))
                row = await cur.fetchone()
                if row:
                    return cls(*row)
                return None
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'org_unit_id': self.org_unit_id,
            'parent_org_unit_id': self.parent_org_unit_id,
            'unit_type': self.unit_type,
            'name': self.name
        }
