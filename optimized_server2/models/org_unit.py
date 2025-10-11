"""
Модель для работы с организационными единицами
"""
from typing import Optional
from datetime import datetime
import aiomysql


class OrgUnit:
    """Модель организационной единицы"""
    
    def __init__(self, org_unit_id: int, parent_org_unit_id: Optional[int], 
                 unit_type: str, name: str, adress: Optional[str] = None,
                 logo_url: Optional[str] = None, created_at: Optional[datetime] = None,
                 default_powerbank_limit: int = 1, reminder_hours: int = 24):
        self.org_unit_id = org_unit_id
        self.parent_org_unit_id = parent_org_unit_id
        self.unit_type = unit_type
        self.name = name
        self.adress = adress
        self.logo_url = logo_url
        self.created_at = created_at
        self.default_powerbank_limit = default_powerbank_limit
        self.reminder_hours = reminder_hours
    
    @classmethod
    async def get_by_id(cls, db_pool, org_unit_id: int) -> Optional['OrgUnit']:
        """Получает организационную единицу по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT org_unit_id, parent_org_unit_id, unit_type, name, adress, logo_url, created_at, default_powerbank_limit, reminder_hours
                    FROM org_unit
                    WHERE org_unit_id = %s
                """, (org_unit_id,))
                row = await cur.fetchone()
                if row:
                    return cls(
                        org_unit_id=row[0],
                        parent_org_unit_id=row[1],
                        unit_type=row[2],
                        name=row[3],
                        adress=row[4],
                        logo_url=row[5],
                        created_at=row[6],
                        default_powerbank_limit=row[7] or 1,
                        reminder_hours=row[8] or 24
                    )
                return None
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'org_unit_id': self.org_unit_id,
            'parent_org_unit_id': self.parent_org_unit_id,
            'unit_type': self.unit_type,
            'name': self.name,
            'adress': self.adress,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'default_powerbank_limit': self.default_powerbank_limit,
            'reminder_hours': self.reminder_hours
        }
