"""
Модель соединения со станцией
"""
from typing import Optional, Dict, Any, List
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
        self.inventory_requested = False
        self.connected_at = get_moscow_time()
        self.last_db_update = None
    
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
        current_time = get_moscow_time()
        self.last_heartbeat = current_time
        self.last_seen = current_time
    
    def update_login(self, box_id: str, station_id: int, token: int, secret_key: bytes):
        """Обновляет данные после логина"""
        self.box_id = box_id
        self.station_id = station_id
        self.token = token
        self.secret_key = secret_key
        self.station_status = "active"
        self.inventory_requested = False
        self.last_db_update = None
        self.update_heartbeat()
    


class ConnectionManager:
    """Менеджер соединений"""
    
    def __init__(self):
        self.connections: Dict[int, StationConnection] = {}
    
    def add_connection(self, connection: StationConnection):
        """Добавляет соединение"""
        # Проверяем, есть ли уже соединение с таким fd
        if connection.fd in self.connections:
            print(f"Соединение с fd={connection.fd} уже существует, заменяем")
            self.remove_connection(connection.fd)
        
        self.connections[connection.fd] = connection
    
    def close_old_station_connections(self, station_id: int, keep_fd: int):
        """Закрывает старые соединения станции, оставляя только указанное"""
        connections_to_close = []
        for fd, conn in self.connections.items():
            if conn.station_id == station_id and fd != keep_fd:
                connections_to_close.append(fd)
        
        for fd in connections_to_close:
            print(f"Закрываем старое соединение станции {station_id} (fd={fd})")
            self.close_connection(fd)
        
        return len(connections_to_close)
    
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
    
    def get_connection_by_station_id(self, station_id: int) -> Optional[StationConnection]:
        """Получает первое соединение по ID станции"""
        for conn in self.connections.values():
            if conn.station_id == station_id:
                return conn
        return None
    
    def cleanup_inactive_connections(self, timeout_seconds: int = 30):
        """Очищает неактивные соединения - закрывает соединения без heartbeat > 30 секунд"""
        current_time = get_moscow_time()
        inactive_fds = []
        
        for fd, connection in self.connections.items():
            if (current_time - connection.last_heartbeat).total_seconds() > timeout_seconds:
                inactive_fds.append(fd)
        
        # Физически закрываем неактивные соединения
        for fd in inactive_fds:
            connection = self.connections.get(fd)
            if connection and connection.writer and not connection.writer.is_closing():
                try:
                    connection.writer.close()
                    # Правильно очищаем callback
                    if hasattr(connection.writer, '_transport') and connection.writer._transport:
                        connection.writer._transport._read_ready_cb = None
                    print(f"СЕРВЕР ЗАКРЫЛ СОЕДИНЕНИЕ: {connection.box_id} (fd={fd}) - нет heartbeat {timeout_seconds} сек")
                except Exception as e:
                    print(f"Ошибка закрытия соединения {fd}: {e}")
            self.remove_connection(fd)
        
        return len(inactive_fds)
    
    def close_connection(self, fd: int):
        """Принудительно закрывает соединение"""
        if fd in self.connections:
            connection = self.connections[fd]
            if connection.writer and not connection.writer.is_closing():
                try:
                    # Правильно закрываем writer
                    connection.writer.close()
                    # Ждем завершения закрытия
                    if hasattr(connection.writer, '_transport') and connection.writer._transport:
                        connection.writer._transport._read_ready_cb = None
                except Exception as e:
                    # Игнорируем ошибки закрытия для сброшенных соединений
                    if not isinstance(e, (ConnectionResetError, OSError, socket.error)):
                        print(f"Ошибка закрытия соединения {fd}: {e}")
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
    
    def get_connections_by_station_id(self, station_id: int) -> List[StationConnection]:
        """Получает все соединения по ID станции"""
        return [conn for conn in self.connections.values() 
                if conn.station_id == station_id]