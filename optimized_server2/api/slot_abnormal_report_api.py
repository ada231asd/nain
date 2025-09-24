"""
API для отчетов об аномалиях слотов
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.station import Station


class SlotAbnormalReportAPI:
    """API для отчетов об аномалиях слотов"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def get_station_abnormal_reports(self, station_id: int, limit: int = 50) -> Dict[str, Any]:
        """
        Получает отчеты об аномалиях слотов станции из базы данных
        """
        try:
            from handlers.slot_abnormal_report import SlotAbnormalReportHandler
            report_handler = SlotAbnormalReportHandler(self.db_pool, self.connection_manager)
            
            result = await report_handler.get_station_abnormal_reports(station_id, limit)
            return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения отчетов об аномалиях: {str(e)}"
            }
    
    async def get_all_abnormal_reports(self, limit: int = 100) -> Dict[str, Any]:
        """
        Получает все отчеты об аномалиях слотов из базы данных
        """
        try:
            from handlers.slot_abnormal_report import SlotAbnormalReportHandler
            report_handler = SlotAbnormalReportHandler(self.db_pool, self.connection_manager)
            
            result = await report_handler.get_all_abnormal_reports(limit)
            return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения всех отчетов об аномалиях: {str(e)}"
            }
    
    async def get_abnormal_reports_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по отчетам об аномалиях слотов
        """
        try:
            from handlers.slot_abnormal_report import SlotAbnormalReportHandler
            report_handler = SlotAbnormalReportHandler(self.db_pool, self.connection_manager)
            
            result = await report_handler.get_abnormal_reports_statistics()
            return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения статистики отчетов об аномалиях: {str(e)}"
            }
    
    async def get_abnormal_reports_by_event_type(self, event_type: int, limit: int = 50) -> Dict[str, Any]:
        """
        Получает отчеты об аномалиях по типу события
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            sar.report_id,
                            sar.station_id,
                            s.box_id,
                            sar.slot_number,
                            sar.terminal_id,
                            sar.event_type,
                            sar.event_text,
                            sar.reported_at,
                            sar.created_at
                        FROM slot_abnormal_reports sar
                        LEFT JOIN station s ON sar.station_id = s.station_id
                        WHERE sar.event_type = %s
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (event_type, limit))
                    reports_data = await cur.fetchall()
            
            reports = []
            for report_data in reports_data:
                report = {
                    "report_id": report_data[0],
                    "station_id": report_data[1],
                    "box_id": report_data[2],
                    "slot_number": report_data[3],
                    "terminal_id": report_data[4],
                    "event_type": report_data[5],
                    "event_text": report_data[6],
                    "reported_at": report_data[7].isoformat() if report_data[7] else None,
                    "created_at": report_data[8].isoformat() if report_data[8] else None
                }
                reports.append(report)
            
            return {
                "success": True,
                "event_type": event_type,
                "reports_count": len(reports),
                "reports": reports
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения отчетов по типу события: {str(e)}"
            }
    
    async def get_abnormal_reports_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> Dict[str, Any]:
        """
        Получает отчеты об аномалиях за период времени
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            sar.report_id,
                            sar.station_id,
                            s.box_id,
                            sar.slot_number,
                            sar.terminal_id,
                            sar.event_type,
                            sar.event_text,
                            sar.reported_at,
                            sar.created_at
                        FROM slot_abnormal_reports sar
                        LEFT JOIN station s ON sar.station_id = s.station_id
                        WHERE sar.reported_at BETWEEN %s AND %s
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (start_date, end_date, limit))
                    reports_data = await cur.fetchall()
            
            reports = []
            for report_data in reports_data:
                report = {
                    "report_id": report_data[0],
                    "station_id": report_data[1],
                    "box_id": report_data[2],
                    "slot_number": report_data[3],
                    "terminal_id": report_data[4],
                    "event_type": report_data[5],
                    "event_text": report_data[6],
                    "reported_at": report_data[7].isoformat() if report_data[7] else None,
                    "created_at": report_data[8].isoformat() if report_data[8] else None
                }
                reports.append(report)
            
            return {
                "success": True,
                "start_date": start_date,
                "end_date": end_date,
                "reports_count": len(reports),
                "reports": reports
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения отчетов за период: {str(e)}"
            }
    
    async def delete_abnormal_report(self, report_id: int) -> Dict[str, Any]:
        """
        Удаляет отчет об аномалии по ID
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        DELETE FROM slot_abnormal_reports 
                        WHERE report_id = %s
                    """, (report_id,))
                    deleted_rows = cur.rowcount
                    await conn.commit()
            
            if deleted_rows > 0:
                return {
                    "success": True,
                    "message": f"Отчет об аномалии {report_id} удален"
                }
            else:
                return {
                    "success": False,
                    "message": "Отчет об аномалии не найден"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка удаления отчета об аномалии: {str(e)}"
            }
