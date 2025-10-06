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
            from models.slot_abnormal_report import SlotAbnormalReport
            
            reports = await SlotAbnormalReport.get_by_station(self.db_pool, station_id, limit)
            reports_data = [report.to_dict() for report in reports]
            
            return {
                "success": True,
                "station_id": station_id,
                "reports_count": len(reports_data),
                "reports": reports_data
            }
                
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
            from models.slot_abnormal_report import SlotAbnormalReport
            
            reports = await SlotAbnormalReport.get_all(self.db_pool, limit)
            reports_data = [report.to_dict() for report in reports]
            
            return {
                "success": True,
                "reports_count": len(reports_data),
                "reports": reports_data
            }
                
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
            from models.slot_abnormal_report import SlotAbnormalReport
            
            statistics = await SlotAbnormalReport.get_statistics(self.db_pool)
            
            return {
                "success": True,
                "statistics": statistics
            }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения статистики отчетов об аномалиях: {str(e)}"
            }
    
    async def get_abnormal_reports_by_event_type(self, event_type: str, limit: int = 50) -> Dict[str, Any]:
        """
        Получает отчеты об аномалиях по типу события
        """
        try:
            from models.slot_abnormal_report import SlotAbnormalReport
            
            reports = await SlotAbnormalReport.get_by_event_type(self.db_pool, event_type, limit)
            reports_data = [report.to_dict() for report in reports]
            
            return {
                "success": True,
                "event_type": event_type,
                "reports_count": len(reports_data),
                "reports": reports_data
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
            from models.slot_abnormal_report import SlotAbnormalReport
            
            reports = await SlotAbnormalReport.get_by_date_range(self.db_pool, start_date, end_date, limit)
            reports_data = [report.to_dict() for report in reports]
            
            return {
                "success": True,
                "start_date": start_date,
                "end_date": end_date,
                "reports_count": len(reports_data),
                "reports": reports_data
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
            from models.slot_abnormal_report import SlotAbnormalReport
            
            success = await SlotAbnormalReport.delete_by_id(self.db_pool, report_id)
            
            if success:
                # Отправляем уведомление через WebSocket об удалении
                try:
                    from websocket_server import websocket_manager
                    await websocket_manager.broadcast({
                        "type": "abnormal_report_deleted",
                        "report_id": report_id,
                        "timestamp": None
                    })
                except Exception as ws_error:
                    print(f"Ошибка отправки WebSocket уведомления об удалении: {ws_error}")
                
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
