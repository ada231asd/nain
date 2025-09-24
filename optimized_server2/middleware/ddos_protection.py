"""
Защита от DDoS атак
"""
import asyncio
import time
from typing import Dict, Set, Optional
from collections import defaultdict, deque
from aiohttp import web
import json


class DDoSProtection:
    """Класс для защиты от DDoS атак"""
    
    def __init__(self):
        # Настройки защиты
        self.max_requests_per_minute = 60
        self.max_requests_per_hour = 1000
        self.block_duration = 300  # 5 минут
        self.cleanup_interval = 3600  # 1 час
        
        # Хранилище данных
        self.request_counts: Dict[str, deque] = defaultdict(lambda: deque())
        self.hourly_counts: Dict[str, int] = defaultdict(int)
        self.blocked_ips: Set[str] = set()
        self.block_times: Dict[str, float] = {}
        
        # Статистика
        self.total_requests = 0
        self.blocked_requests = 0
        self.attack_detections = 0
        
        # Запускаем очистку
        asyncio.create_task(self._cleanup_loop())
    
    async def check_request(self, client_ip: str) -> bool:
        """Проверяет, разрешен ли запрос"""
        current_time = time.time()
        
        # Проверяем, не заблокирован ли IP
        if client_ip in self.blocked_ips:
            if current_time - self.block_times.get(client_ip, 0) > self.block_duration:
                # Разблокируем IP
                self.blocked_ips.discard(client_ip)
                self.block_times.pop(client_ip, None)
            else:
                self.blocked_requests += 1
                return False
        
        # Очищаем старые записи для минутного лимита
        while (self.request_counts[client_ip] and 
               current_time - self.request_counts[client_ip][0] > 60):
            self.request_counts[client_ip].popleft()
        
        # Проверяем минутный лимит
        if len(self.request_counts[client_ip]) >= self.max_requests_per_minute:
            await self._block_ip(client_ip, current_time)
            return False
        
        # Проверяем часовой лимит
        if self.hourly_counts[client_ip] >= self.max_requests_per_hour:
            await self._block_ip(client_ip, current_time)
            return False
        
        # Добавляем запрос
        self.request_counts[client_ip].append(current_time)
        self.hourly_counts[client_ip] += 1
        self.total_requests += 1
        
        return True
    
    async def _block_ip(self, client_ip: str, current_time: float):
        """Блокирует IP адрес"""
        self.blocked_ips.add(client_ip)
        self.block_times[client_ip] = current_time
        self.attack_detections += 1
        
        print(f"DDoS Protection: IP {client_ip} заблокирован за превышение лимитов")
    
    async def _cleanup_loop(self):
        """Цикл очистки устаревших данных"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_data()
            except Exception as e:
                print(f"Ошибка в цикле очистки DDoS защиты: {e}")
    
    async def _cleanup_expired_data(self):
        """Очищает устаревшие данные"""
        current_time = time.time()
        
        # Очищаем заблокированные IP
        expired_ips = []
        for ip, block_time in self.block_times.items():
            if current_time - block_time > self.block_duration:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            self.blocked_ips.discard(ip)
            self.block_times.pop(ip, None)
        
        # Очищаем старые счетчики
        expired_ips = []
        for ip in self.request_counts:
            if not self.request_counts[ip]:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            del self.request_counts[ip]
            self.hourly_counts.pop(ip, None)
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику защиты"""
        return {
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'attack_detections': self.attack_detections,
            'blocked_ips_count': len(self.blocked_ips),
            'active_ips_count': len(self.request_counts)
        }


class RateLimiter:
    """Класс для ограничения скорости запросов"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    async def is_allowed(self, client_ip: str) -> bool:
        """Проверяет, разрешен ли запрос"""
        current_time = time.time()
        
        # Очищаем старые записи
        while (self.requests[client_ip] and 
               current_time - self.requests[client_ip][0] > self.time_window):
            self.requests[client_ip].popleft()
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Добавляем запрос
        self.requests[client_ip].append(current_time)
        return True
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Возвращает количество оставшихся запросов"""
        current_time = time.time()
        
        # Очищаем старые записи
        while (self.requests[client_ip] and 
               current_time - self.requests[client_ip][0] > self.time_window):
            self.requests[client_ip].popleft()
        
        return max(0, self.max_requests - len(self.requests[client_ip]))


class ConnectionLimiter:
    """Класс для ограничения количества соединений"""
    
    def __init__(self, max_connections: int = 1000):
        self.max_connections = max_connections
        self.active_connections: Set[str] = set()
        self.connection_times: Dict[str, float] = {}
    
    async def add_connection(self, client_ip: str) -> bool:
        """Добавляет соединение"""
        if len(self.active_connections) >= self.max_connections:
            return False
        
        self.active_connections.add(client_ip)
        self.connection_times[client_ip] = time.time()
        return True
    
    def remove_connection(self, client_ip: str):
        """Удаляет соединение"""
        self.active_connections.discard(client_ip)
        self.connection_times.pop(client_ip, None)
    
    def get_connection_count(self) -> int:
        """Возвращает количество активных соединений"""
        return len(self.active_connections)
    
    def cleanup_expired_connections(self, timeout: int = 300):
        """Очищает устаревшие соединения"""
        current_time = time.time()
        expired_ips = []
        
        for ip, conn_time in self.connection_times.items():
            if current_time - conn_time > timeout:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            self.remove_connection(ip)


def create_ddos_protection():
    """Создает экземпляр защиты от DDoS"""
    return DDoSProtection()


def create_rate_limiter(max_requests: int = 100, time_window: int = 60):
    """Создает экземпляр ограничителя скорости"""
    return RateLimiter(max_requests, time_window)


def create_connection_limiter(max_connections: int = 1000):
    """Создает экземпляр ограничителя соединений"""
    return ConnectionLimiter(max_connections)

