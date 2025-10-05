"""
Модель соединения со станцией
"""
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from utils.time_utils import get_moscow_time
import socket


class StationConnection:
    """Модель соединения со станцией"""
    
    def __init__(self, fd: int, addr: tuple, box_id: str = "unknown", 
                 station_id: Optional[int] = None, writer: Optional[asyncio.StreamWriter] = None):
        self.fd = fd
        self.addr = addr
        self.box_id = box_id
        self.station_id = station_id
        self.writer = writer
        self.last_seen = get_moscow_time()
        self.last_heartbeat = get_moscow_time()
        self.token: Optional[int] = None
        self.secret_key: Optional[bytes] = None
        self.station_status = "pending"
        self.borrow_sent = False
        self.suspicious_packets = 0  # Счетчик подозрительных пакетов
        self.inventory_requested = False  # Флаг запроса инвентаря при логине
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует соединение в словарь"""
        return {
            "fd": self.fd,
            "addr": self.addr,
            "boxid": self.box_id,
            "station_id": self.station_id,
            "last_seen": self.last_seen.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "token": self.token,
            "station_status": self.station_status,
            "borrow_sent": self.borrow_sent
        }
    
    def update_heartbeat(self):
        """Обновляет время последнего heartbeat"""
        self.last_heartbeat = get_moscow_time()
        self.last_seen = get_moscow_time()
    
    def update_login(self, box_id: str, station_id: int, token: int, secret_key: bytes):
        """Обновляет данные после логина"""
        self.box_id = box_id
        self.station_id = station_id
        self.token = token
        self.secret_key = secret_key
        self.station_status = "active"
        self.inventory_requested = False  # Сбрасываем флаг при новом логине
        self.update_heartbeat()
    
    def increment_suspicious_packets(self):
        """Увеличивает счетчик подозрительных пакетов"""
        self.suspicious_packets += 1
    
    def reset_suspicious_packets(self):
        """Сбрасывает счетчик подозрительных пакетов"""
        self.suspicious_packets = 0
    
    def is_too_suspicious(self, max_packets: int) -> bool:
        """Проверяет, не слишком ли много подозрительных пакетов"""
        return self.suspicious_packets >= max_packets


class ConnectionManager:
    """Менеджер соединений"""
    
    def __init__(self):
        self.connections: Dict[int, StationConnection] = {}
    
    def add_connection(self, connection: StationConnection):
        """Добавляет соединение"""
        # Если станция уже подключена, закрываем старое соединение
        if connection.station_id:
            old_connection = self.get_connection_by_station_id(connection.station_id)
            if old_connection and old_connection.fd != connection.fd:
                print(f"Закрываем старое соединение для станции {connection.station_id} (fd={old_connection.fd})")
                self.remove_connection(old_connection.fd)
        
        self.connections[connection.fd] = connection
    
    def remove_connection(self, fd: int):
        """Удаляет соединение"""
        if fd in self.connections:
            del self.connections[fd]
    
    def get_connection(self, fd: int) -> Optional[StationConnection]:
        """Получает соединение по fd"""
        return self.connections.get(fd)
    
    def get_all_connections(self) -> Dict[int, StationConnection]:
        """Получает все соединения"""
        return self.connections.copy()
    
    def get_connections_by_station_id(self, station_id: int) -> list[StationConnection]:
        """Получает соединения по ID станции"""
        return [conn for conn in self.connections.values() 
                if conn.station_id == station_id]
    
    def get_connection_by_station_id(self, station_id: int) -> Optional[StationConnection]:
        """Получает первое соединение по ID станции"""
        for conn in self.connections.values():
            if conn.station_id == station_id:
                return conn
        return None
    
    def cleanup_inactive_connections(self, timeout_seconds: int = 300):
        """Очищает неактивные соединения"""
        current_time = get_moscow_time()
        inactive_fds = []
        
        for fd, connection in self.connections.items():
            if (current_time - connection.last_heartbeat).seconds > timeout_seconds:
                inactive_fds.append(fd)
        
        for fd in inactive_fds:
            self.remove_connection(fd)
        
        return len(inactive_fds)
    
    def close_connection(self, fd: int):
        """Принудительно закрывает соединение"""
        if fd in self.connections:
            connection = self.connections[fd]
            if connection.writer and not connection.writer.is_closing():
                try:
                    connection.writer.close()
                except Exception as e:
                    # Игнорируем ошибки закрытия для сброшенных соединений
                    if not isinstance(e, (ConnectionResetError, OSError, socket.error)):
                        self.logger.error(f"Ошибка: {e}")
            self.remove_connection(fd)
    
    def close_station_connections(self, station_id: int):
        """Закрывает все соединения станции"""
        connections_to_close = []
        for fd, connection in self.connections.items():
            if connection.station_id == station_id:
                connections_to_close.append(fd)
        
        for fd in connections_to_close:
            self.close_connection(fd)
        
        return len(connections_to_close)
    
    def clear_all_connections(self):
        """Очищает все соединения из менеджера"""
        self.connections.clear()
        print(f"Очищено {len(self.connections)} соединений из менеджера")
