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
                 created_at: Optional[datetime] = None,
                 box_id: Optional[str] = None):
        self.report_id = report_id
        self.station_id = station_id
        self.slot_number = slot_number
        self.terminal_id = terminal_id
        self.event_type = event_type
        self.reported_at = reported_at
        self.created_at = created_at
        self.box_id = box_id
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'report_id': self.report_id,
            'station_id': self.station_id,
            'slot_number': self.slot_number,
            'terminal_id': self.terminal_id,
            'event_type': self.event_type,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'box_id': self.box_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SlotAbnormalReport':
        """Создает экземпляр из словаря"""
        return cls(
            report_id=data.get('report_id'),
            station_id=data.get('station_id'),
            slot_number=data.get('slot_number'),
            terminal_id=data.get('terminal_id'),
            event_type=data.get('event_type'),
            reported_at=data.get('reported_at'),
            created_at=data.get('created_at'),
            box_id=data.get('box_id')
        )
    
    @classmethod
    async def create(
        cls,
        db_pool,
        station_id: int,
        slot_number: int,
        terminal_id: Optional[str],
        event_type: str,
        reported_at: Optional[datetime] = None,
    ) -> 'SlotAbnormalReport':
        """Создает отчет об аномалии."""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                now = datetime.now()
                reported_at_value = reported_at or now
                await cur.execute(
                    """
                    INSERT INTO slot_abnormal_reports (station_id, slot_number, terminal_id, event_type, reported_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (station_id, slot_number, terminal_id, event_type, reported_at_value, now),
                )
                report_id = cur.lastrowid
                return cls(
                    report_id=report_id,
                    station_id=station_id,
                    slot_number=slot_number,
                    terminal_id=terminal_id,
                    event_type=event_type,
                    reported_at=reported_at_value,
                    created_at=now,
                    box_id=None,
                )
    
    @classmethod
    async def get_by_station_id(cls, db_pool, station_id: int, limit: int = 100) -> List['SlotAbnormalReport']:
        """Получает отчеты по станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT r.report_id, r.station_id, r.slot_number, r.terminal_id, r.event_type, r.reported_at, r.created_at,
                           s.box_id
                    FROM slot_abnormal_reports r
                    LEFT JOIN station s ON s.station_id = r.station_id
                    WHERE r.station_id = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (station_id, limit),
                )
                rows = await cur.fetchall()
        
        reports: List[SlotAbnormalReport] = []
        for row in rows:
            reports.append(
                cls(
                    report_id=row[0],
                    station_id=row[1],
                    slot_number=row[2],
                    terminal_id=row[3],
                    event_type=row[4],
                    reported_at=row[5],
                    created_at=row[6],
                    box_id=row[7] if len(row) > 7 else None,
                )
            )
        return reports

    @classmethod
    async def get_by_station(cls, db_pool, station_id: int, limit: int = 100) -> List['SlotAbnormalReport']:
        return await cls.get_by_station_id(db_pool, station_id, limit)

    @classmethod
    async def get_all(cls, db_pool, limit: int = 100) -> List['SlotAbnormalReport']:
        """Получает все отчеты об аномалиях."""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT r.report_id, r.station_id, r.slot_number, r.terminal_id, r.event_type, r.reported_at, r.created_at,
                           s.box_id
                    FROM slot_abnormal_reports r
                    LEFT JOIN station s ON s.station_id = r.station_id
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = await cur.fetchall()
        
        return [
            cls(
                report_id=row[0],
                station_id=row[1],
                slot_number=row[2],
                terminal_id=row[3],
                event_type=row[4],
                reported_at=row[5],
                created_at=row[6],
                box_id=row[7] if len(row) > 7 else None,
            )
            for row in rows
        ]

    @classmethod
    async def get_statistics(cls, db_pool) -> dict:
        """Возвращает статистику по отчетам """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT event_type, COUNT(*)
                    FROM slot_abnormal_reports
                    GROUP BY event_type
                    """
                )
                rows = await cur.fetchall()
                await cur.execute("SELECT COUNT(*) FROM slot_abnormal_reports")
                total_row = await cur.fetchone()
        
        stats = {"by_event_type": {}}
        for row in rows:
            stats["by_event_type"][row[0]] = row[1]
        stats["total"] = total_row[0] if total_row else 0
        return stats

    @classmethod
    async def get_by_event_type(cls, db_pool, event_type: str, limit: int = 50) -> List['SlotAbnormalReport']:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT r.report_id, r.station_id, r.slot_number, r.terminal_id, r.event_type, r.reported_at, r.created_at,
                           s.box_id
                    FROM slot_abnormal_reports r
                    LEFT JOIN station s ON s.station_id = r.station_id
                    WHERE r.event_type = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (event_type, limit),
                )
                rows = await cur.fetchall()
        
        return [
            cls(
                report_id=row[0],
                station_id=row[1],
                slot_number=row[2],
                terminal_id=row[3],
                event_type=row[4],
                reported_at=row[5],
                created_at=row[6],
                box_id=row[7] if len(row) > 7 else None,
            )
            for row in rows
        ]

    @classmethod
    async def get_by_date_range(
        cls, db_pool, start_date: str, end_date: str, limit: int = 100
    ) -> List['SlotAbnormalReport']:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT r.report_id, r.station_id, r.slot_number, r.terminal_id, r.event_type, r.reported_at, r.created_at,
                           s.box_id
                    FROM slot_abnormal_reports r
                    LEFT JOIN station s ON s.station_id = r.station_id
                    WHERE r.created_at BETWEEN %s AND %s
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (start_date, end_date, limit),
                )
                rows = await cur.fetchall()
        
        return [
            cls(
                report_id=row[0],
                station_id=row[1],
                slot_number=row[2],
                terminal_id=row[3],
                event_type=row[4],
                reported_at=row[5],
                created_at=row[6],
                box_id=row[7] if len(row) > 7 else None,
            )
            for row in rows
        ]

    @classmethod
    async def delete_by_id(cls, db_pool, report_id: int) -> bool:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM slot_abnormal_reports WHERE report_id = %s",
                    (report_id,),
                )
                return cur.rowcount > 0

    @classmethod
    async def get_by_id(cls, db_pool, report_id: int) -> Optional['SlotAbnormalReport']:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT r.report_id, r.station_id, r.slot_number, r.terminal_id, r.event_type, r.reported_at, r.created_at,
                           s.box_id
                    FROM slot_abnormal_reports r
                    LEFT JOIN station s ON s.station_id = r.station_id
                    WHERE r.report_id = %s
                    """,
                    (report_id,),
                )
                row = await cur.fetchone()
        
        if not row:
            return None
        
        return cls(
            report_id=row[0],
            station_id=row[1],
            slot_number=row[2],
            terminal_id=row[3],
            event_type=row[4],
            reported_at=row[5],
            created_at=row[6],
            box_id=row[7] if len(row) > 7 else None,
        )