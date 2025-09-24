"""
API для запроса ICCID SIM карт станций
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.station import Station


class QueryICCIDAPI:
    """API для запроса ICCID SIM карт станций"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def query_station_iccid(self, station_id: int) -> Dict[str, Any]:
        """
        Отправляет запрос ICCID на станцию
        """
        try:
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {
                    "success": False,
                    "message": "Станция не найдена"
                }
            
            # Проверяем, что станция активна
            if station.status != 'active':
                return {
                    "success": False,
                    "message": "Станция неактивна"
                }
            
            # Проверяем подключение станции
            if not self.connection_manager:
                return {
                    "success": False,
                    "message": "Connection manager недоступен"
                }
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {
                    "success": False,
                    "message": "Станция не подключена"
                }
            
            # Создаем команду запроса ICCID
            from handlers.query_iccid import QueryICCIDHandler
            iccid_handler = QueryICCIDHandler(self.db_pool, self.connection_manager)
            
            result = await iccid_handler.send_query_iccid_command(station_id)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Команда запроса ICCID отправлена на станцию {station.box_id}",
                    "station_id": station_id,
                    "box_id": station.box_id,
                    "sent_at": datetime.now().isoformat()
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка отправки команды ICCID: {str(e)}"
            }
    
    async def get_station_iccid(self, station_id: int) -> Dict[str, Any]:
        """
        Получает сохраненный ICCID станции из базы данных
        """
        try:
            from handlers.query_iccid import QueryICCIDHandler
            iccid_handler = QueryICCIDHandler(self.db_pool, self.connection_manager)
            
            result = await iccid_handler.get_station_iccid(station_id)
            return result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения ICCID: {str(e)}"
            }
    
    async def get_all_stations_iccid(self) -> Dict[str, Any]:
        """
        Получает ICCID всех станций из базы данных
        """
        try:
            # Получаем все станции с ICCID
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            station_id,
                            box_id,
                            org_unit_id,
                            status,
                            iccid,
                            updated_at,
                            last_seen
                        FROM station 
                        ORDER BY station_id
                    """)
                    stations_data = await cur.fetchall()
            
            stations_info = []
            for station_data in stations_data:
                station_info = {
                    "station_id": station_data[0],
                    "box_id": station_data[1],
                    "org_unit_id": station_data[2],
                    "status": station_data[3],
                    "iccid": station_data[4],
                    "iccid_updated_at": station_data[5].isoformat() if station_data[5] else None,
                    "last_seen": station_data[6].isoformat() if station_data[6] else None,
                    "has_iccid": station_data[4] is not None
                }
                stations_info.append(station_info)
            
            # Статистика
            total_stations = len(stations_info)
            stations_with_iccid = len([s for s in stations_info if s["has_iccid"]])
            active_stations = len([s for s in stations_info if s["status"] == "active"])
            
            return {
                "success": True,
                "total_stations": total_stations,
                "stations_with_iccid": stations_with_iccid,
                "active_stations": active_stations,
                "stations": stations_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения ICCID станций: {str(e)}"
            }
    
    async def query_multiple_stations_iccid(self, station_ids: List[int]) -> Dict[str, Any]:
        """
        Отправляет запросы ICCID на несколько станций
        """
        try:
            results = []
            success_count = 0
            error_count = 0
            
            for station_id in station_ids:
                result = await self.query_station_iccid(station_id)
                results.append({
                    "station_id": station_id,
                    "result": result
                })
                
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1
            
            return {
                "success": True,
                "message": f"Обработано {len(station_ids)} станций",
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка массового запроса ICCID: {str(e)}"
            }
    
    async def get_iccid_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по ICCID станций
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Общая статистика
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as total_stations,
                            COUNT(iccid) as stations_with_iccid,
                            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_stations,
                            COUNT(CASE WHEN status = 'active' AND iccid IS NOT NULL THEN 1 END) as active_with_iccid
                        FROM station
                    """)
                    stats = await cur.fetchone()
                    
                    # Статистика по обновлению ICCID
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as total_with_iccid,
                            COUNT(CASE WHEN updated_at > DATE_SUB(NOW(), INTERVAL 1 DAY) THEN 1 END) as updated_today,
                            COUNT(CASE WHEN updated_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as updated_week,
                            COUNT(CASE WHEN updated_at > DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as updated_month
                        FROM station 
                        WHERE iccid IS NOT NULL
                    """)
                    update_stats = await cur.fetchone()
            
            return {
                "success": True,
                "statistics": {
                    "total_stations": stats[0],
                    "stations_with_iccid": stats[1],
                    "active_stations": stats[2],
                    "active_with_iccid": stats[3],
                    "iccid_coverage": round((stats[1] / stats[0] * 100), 2) if stats[0] > 0 else 0,
                    "active_iccid_coverage": round((stats[3] / stats[2] * 100), 2) if stats[2] > 0 else 0
                },
                "update_statistics": {
                    "total_with_iccid": update_stats[0],
                    "updated_today": update_stats[1],
                    "updated_week": update_stats[2],
                    "updated_month": update_stats[3]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения статистики ICCID: {str(e)}"
            }
