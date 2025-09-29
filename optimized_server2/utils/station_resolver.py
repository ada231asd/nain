"""
Утилита для автоматического определения станции
"""
from typing import Optional, Dict, Any
from models.connection import ConnectionManager


class StationResolver:
    """Утилита для определения станции по различным параметрам"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    def resolve_station_by_id(self, station_id: int) -> Optional[Dict[str, Any]]:
        """Определяет станцию по ID"""
        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if connection:
            return {
                "station_id": connection.station_id,
                "box_id": connection.box_id,
                "connection": connection,
                "is_connected": True
            }
        return None
    
    def resolve_station_by_box_id(self, box_id: str) -> Optional[Dict[str, Any]]:
        """Определяет станцию по Box ID"""
        for connection in self.connection_manager.get_all_connections().values():
            if connection.box_id == box_id:
                return {
                    "station_id": connection.station_id,
                    "box_id": connection.box_id,
                    "connection": connection,
                    "is_connected": True
                }
        return None
    
    def resolve_station_by_powerbank_id(self, powerbank_id: int, db_pool) -> Optional[Dict[str, Any]]:
        """Определяет станцию по ID повербанка"""
        try:
            
            from models.station_powerbank import StationPowerbank
            
            # Получаем информацию о повербанке в станции
            station_powerbank = StationPowerbank.get_by_powerbank_id(db_pool, powerbank_id)
            if station_powerbank:
                connection = self.connection_manager.get_connection_by_station_id(station_powerbank.station_id)
                return {
                    "station_id": station_powerbank.station_id,
                    "slot_number": station_powerbank.slot_number,
                    "powerbank_id": powerbank_id,
                    "connection": connection,
                    "is_connected": connection is not None
                }
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
        
        return None
    
    def resolve_station_by_slot(self, station_id: int, slot_number: int) -> Optional[Dict[str, Any]]:
        """Определяет станцию по ID и номеру слота"""
        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if connection:
            return {
                "station_id": station_id,
                "slot_number": slot_number,
                "box_id": connection.box_id,
                "connection": connection,
                "is_connected": True
            }
        return None
    
    def get_connection_for_station(self, station_id: int) -> Optional[Any]:
        """Получает TCP соединение для станции"""
        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if connection and connection.writer and not connection.writer.is_closing():
            return connection
        return None
    
    def is_station_connected(self, station_id: int) -> bool:
        """Проверяет подключена ли станция"""
        connection = self.connection_manager.get_connection_by_station_id(station_id)
        return connection is not None and connection.writer is not None and not connection.writer.is_closing()
    
    def get_station_info(self, station_id: int) -> Optional[Dict[str, Any]]:
        """Получает полную информацию о станции"""
        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if connection:
            return {
                "station_id": connection.station_id,
                "box_id": connection.box_id,
                "addr": connection.addr,
                "last_seen": connection.last_seen.isoformat() if connection.last_seen else None,
                "last_heartbeat": connection.last_heartbeat.isoformat() if connection.last_heartbeat else None,
                "station_status": connection.station_status,
                "is_connected": True,
                "has_writer": connection.writer is not None,
                "writer_closed": connection.writer.is_closing() if connection.writer else True
            }
        return None
