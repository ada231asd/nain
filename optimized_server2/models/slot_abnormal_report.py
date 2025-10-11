"""
Модель для работы с отчетами об аномалиях слотов
"""
from typing import Optional, List
from datetime import datetime
import aiomysql


class SlotAbnormalReport:
    """Модель отчета об аномалии слота"""
    
    def __init__(self, report_id: int, station_id: int, slot_number: int, 
                 terminal_id: Optional[str], event_type: str, 
                 reported_at: Optional[datetime] = None, 
                 created_at: Optional[datetime] = None):
        self.report_id = report_id
        self.station_id = station_id
        self.slot_number = slot_number
        self.terminal_id = terminal_id
        self.event_type = event_type
        self.reported_at = reported_at
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'report_id': self.report_id,
            'station_id': self.station_id,
            'slot_number': self.slot_number,
            'terminal_id': self.terminal_id,
            'event_type': self.event_type,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    async def create(cls, db_pool, station_id: int, slot_number: int, 
                    terminal_id: Optional[str], event_type: str) -> 'SlotAbnormalReport':
        """Создает отчет об аномалии"""
        async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                   now = datetime.now()
                await cur.execute("""
                    INSERT INTO slot_abnormal_reports (station_id, slot_number, terminal_id, event_type, reported_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                """, (station_id, slot_number, terminal_id, event_type, now, now))
                
                report_id = cur.lastrowid
                
                return cls(
                    report_id=report_id,
                    station_id=station_id,
                    slot_number=slot_number,
                    terminal_id=terminal_id,
                    event_type=event_type,
                    reported_at=now,
                    created_at=now
                )
    
    @classmethod
    async def get_by_station_id(cls, db_pool, station_id: int, limit: int = 100) -> List['SlotAbnormalReport']:
        """Получает отчеты по станции"""
        async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                    SELECT report_id, station_id, slot_number, terminal_id, event_type, reported_at, created_at
                    FROM slot_abnormal_reports
                    WHERE station_id = %s
                    ORDER BY created_at DESC
                        LIMIT %s
                    """, (station_id, limit))
                rows = await cur.fetchall()
                
                reports = []
                for row in rows:
                    reports.append(cls(
                        report_id=row[0],
                        station_id=row[1],
                        slot_number=row[2],
                        terminal_id=row[3],
                        event_type=row[4],
                        reported_at=row[5],
                        created_at=row[6]
                    ))
                return reports