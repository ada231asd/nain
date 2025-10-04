"""
Модель для отчетов об аномалиях слотов станций
"""
from typing import Optional, List, Dict, Any
import aiomysql
from utils.time_utils import get_moscow_time


class SlotAbnormalReport:
    """Модель отчета об аномалии слота"""
    
    def __init__(self, report_id: int, station_id: int, slot_number: int, 
                 terminal_id: Optional[str], event_type: str, event_text: Optional[str],
                 reported_at: Optional[str], created_at: Optional[str]):
        self.report_id = report_id
        self.station_id = station_id
        self.slot_number = slot_number
        self.terminal_id = terminal_id
        self.event_type = event_type
        self.event_text = event_text
        self.reported_at = reported_at
        self.created_at = created_at
    
    @classmethod
    async def create(cls, db_pool, station_id: int, slot_number: int, 
                    terminal_id: Optional[str], event_type: str, event_text: Optional[str],
                    reported_at: Optional[str] = None) -> Optional['SlotAbnormalReport']:
        """
        Создает новый отчет об аномалии слота
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO slot_abnormal_reports 
                        (station_id, slot_number, terminal_id, event_type, event_text, 
                         reported_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        station_id,
                        slot_number,
                        terminal_id,
                        event_type,
                        event_text,
                        reported_at,
                        get_moscow_time()
                    ))
                    await conn.commit()
                    
                    # Получаем созданный отчет
                    report_id = cur.lastrowid
                    return await cls.get_by_id(db_pool, report_id)
                    
        except Exception as e:
            print(f"Ошибка создания отчета об аномалии: {e}")
            return None
    
    @classmethod
    async def get_by_id(cls, db_pool, report_id: int) -> Optional['SlotAbnormalReport']:
        """
        Получает отчет об аномалии по ID
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT report_id, station_id, slot_number, terminal_id, 
                               event_type, event_text, reported_at, created_at
                        FROM slot_abnormal_reports 
                        WHERE report_id = %s
                    """, (report_id,))
                    
                    result = await cur.fetchone()
                    if result:
                        return cls(*result)
                    return None
                    
        except Exception as e:
            print(f"Ошибка получения отчета об аномалии: {e}")
            return None
    
    @classmethod
    async def get_by_station(cls, db_pool, station_id: int, limit: int = 50) -> List['SlotAbnormalReport']:
        """
        Получает отчеты об аномалиях для станции
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT report_id, station_id, slot_number, terminal_id, 
                               event_type, event_text, reported_at, created_at
                        FROM slot_abnormal_reports 
                        WHERE station_id = %s
                        ORDER BY reported_at DESC
                        LIMIT %s
                    """, (station_id, limit))
                    
                    results = await cur.fetchall()
                    return [cls(*result) for result in results]
                    
        except Exception as e:
            print(f"Ошибка получения отчетов об аномалиях станции: {e}")
            return []
    
    @classmethod
    async def get_all(cls, db_pool, limit: int = 100) -> List['SlotAbnormalReport']:
        """
        Получает все отчеты об аномалиях
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT sar.report_id, sar.station_id, sar.slot_number, 
                               sar.terminal_id, sar.event_type, sar.event_text, 
                               sar.reported_at, sar.created_at
                        FROM slot_abnormal_reports sar
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (limit,))
                    
                    results = await cur.fetchall()
                    return [cls(*result) for result in results]
                    
        except Exception as e:
            print(f"Ошибка получения всех отчетов об аномалиях: {e}")
            return []
    
    @classmethod
    async def get_by_event_type(cls, db_pool, event_type: str, limit: int = 50) -> List['SlotAbnormalReport']:
        """
        Получает отчеты об аномалиях по типу события
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT sar.report_id, sar.station_id, sar.slot_number, 
                               sar.terminal_id, sar.event_type, sar.event_text, 
                               sar.reported_at, sar.created_at
                        FROM slot_abnormal_reports sar
                        WHERE sar.event_type = %s
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (event_type, limit))
                    
                    results = await cur.fetchall()
                    return [cls(*result) for result in results]
                    
        except Exception as e:
            print(f"Ошибка получения отчетов по типу события: {e}")
            return []
    
    @classmethod
    async def get_by_date_range(cls, db_pool, start_date: str, end_date: str, limit: int = 100) -> List['SlotAbnormalReport']:
        """
        Получает отчеты об аномалиях за период времени
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT sar.report_id, sar.station_id, sar.slot_number, 
                               sar.terminal_id, sar.event_type, sar.event_text, 
                               sar.reported_at, sar.created_at
                        FROM slot_abnormal_reports sar
                        WHERE sar.reported_at BETWEEN %s AND %s
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (start_date, end_date, limit))
                    
                    results = await cur.fetchall()
                    return [cls(*result) for result in results]
                    
        except Exception as e:
            print(f"Ошибка получения отчетов за период: {e}")
            return []
    
    @classmethod
    async def delete_by_id(cls, db_pool, report_id: int) -> bool:
        """
        Удаляет отчет об аномалии по ID
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        DELETE FROM slot_abnormal_reports 
                        WHERE report_id = %s
                    """, (report_id,))
                    await conn.commit()
                    return cur.rowcount > 0
                    
        except Exception as e:
            print(f"Ошибка удаления отчета об аномалии: {e}")
            return False
    
    @classmethod
    async def get_statistics(cls, db_pool) -> Dict[str, Any]:
        """
        Получает статистику по отчетам об аномалиях
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Общая статистика
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as total_reports,
                            COUNT(DISTINCT station_id) as stations_with_reports,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 1 DAY) THEN 1 END) as reports_today,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as reports_week,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as reports_month
                        FROM slot_abnormal_reports
                    """)
                    stats = await cur.fetchone()
                    
                    # Статистика по типам событий
                    await cur.execute("""
                        SELECT 
                            event_type,
                            event_text,
                            COUNT(*) as count
                        FROM slot_abnormal_reports 
                        GROUP BY event_type, event_text
                        ORDER BY count DESC
                    """)
                    event_stats = await cur.fetchall()
                    
                    # Статистика по станциям
                    await cur.execute("""
                        SELECT 
                            s.station_id,
                            s.box_id,
                            COUNT(sar.report_id) as reports_count
                        FROM station s
                        LEFT JOIN slot_abnormal_reports sar ON s.station_id = sar.station_id
                        GROUP BY s.station_id, s.box_id
                        ORDER BY reports_count DESC
                        LIMIT 10
                    """)
                    station_stats = await cur.fetchall()
            
            return {
                "total_reports": stats[0],
                "stations_with_reports": stats[1],
                "reports_today": stats[2],
                "reports_week": stats[3],
                "reports_month": stats[4],
                "event_statistics": [
                    {
                        "event_type": row[0],
                        "event_text": row[1],
                        "count": row[2]
                    } 
                    for row in event_stats
                ],
                "station_statistics": [
                    {
                        "station_id": row[0],
                        "box_id": row[1],
                        "reports_count": row[2]
                    } 
                    for row in station_stats
                ]
            }
            
        except Exception as e:
            print(f"Ошибка получения статистики отчетов об аномалиях: {e}")
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь
        """
        return {
            "report_id": self.report_id,
            "station_id": self.station_id,
            "slot_number": self.slot_number,
            "terminal_id": self.terminal_id,
            "event_type": self.event_type,
            "event_text": self.event_text,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
