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
    
    async def get_all_abnormal_reports(self, limit: int = 100, accessible_org_units=None) -> Dict[str, Any]:
        """
        Получает все отчеты об аномалиях слотов из базы данных
        """
        try:
            import aiomysql
            from models.slot_abnormal_report import SlotAbnormalReport
            
            # Если есть фильтр по org_units, применяем его
            if accessible_org_units is not None:
                if len(accessible_org_units) == 0:
                    return {
                        "success": True,
                        "reports_count": 0,
                        "reports": []
                    }
                
                # Получаем отчеты с фильтрацией по org_unit станций
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        placeholders = ','.join(['%s'] * len(accessible_org_units))
                        query = f"""
                            SELECT sar.* FROM slot_abnormal_reports sar
                            INNER JOIN station s ON sar.station_id = s.station_id
                            WHERE s.org_unit_id IN ({placeholders})
                            ORDER BY sar.created_at DESC
                            LIMIT %s
                        """
                        await cur.execute(query, accessible_org_units + [limit])
                        rows = await cur.fetchall()
                        
                        reports_data = []
                        for row in rows:
                            report = SlotAbnormalReport.from_dict(row)
                            reports_data.append(report.to_dict())
                        
                        return {
                            "success": True,
                            "reports_count": len(reports_data),
                            "reports": reports_data
                        }
            else:
                # Без фильтрации (service_admin)
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
    
    async def get_abnormal_reports_statistics(self, accessible_org_units=None) -> Dict[str, Any]:
        """
        Получает статистику по отчетам об аномалиях слотов
        """
        try:
            import aiomysql
            from models.slot_abnormal_report import SlotAbnormalReport
            
            # Если есть фильтр по org_units, применяем его
            if accessible_org_units is not None:
                if len(accessible_org_units) == 0:
                    return {
                        "success": True,
                        "statistics": {
                            "total_reports": 0,
                            "by_event_type": {},
                            "by_station": []
                        }
                    }
                
                # Получаем статистику с фильтрацией
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        placeholders = ','.join(['%s'] * len(accessible_org_units))
                        
                        # Общее количество
                        await cur.execute(f"""
                            SELECT COUNT(*) as total
                            FROM slot_abnormal_reports sar
                            INNER JOIN station s ON sar.station_id = s.station_id
                            WHERE s.org_unit_id IN ({placeholders})
                        """, accessible_org_units)
                        total = (await cur.fetchone())['total']
                        
                        # По типам событий
                        await cur.execute(f"""
                            SELECT sar.event_type, COUNT(*) as count
                            FROM slot_abnormal_reports sar
                            INNER JOIN station s ON sar.station_id = s.station_id
                            WHERE s.org_unit_id IN ({placeholders})
                            GROUP BY sar.event_type
                        """, accessible_org_units)
                        by_event_type = {row['event_type']: row['count'] for row in await cur.fetchall()}
                        
                        # По станциям
                        await cur.execute(f"""
                            SELECT s.station_id, s.box_id, COUNT(*) as count
                            FROM slot_abnormal_reports sar
                            INNER JOIN station s ON sar.station_id = s.station_id
                            WHERE s.org_unit_id IN ({placeholders})
                            GROUP BY s.station_id, s.box_id
                            ORDER BY count DESC
                            LIMIT 10
                        """, accessible_org_units)
                        by_station = [dict(row) for row in await cur.fetchall()]
                        
                        statistics = {
                            "total_reports": total,
                            "by_event_type": by_event_type,
                            "by_station": by_station
                        }
                        
                        return {
                            "success": True,
                            "statistics": statistics
                        }
            else:
                # Без фильтрации (service_admin)
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
