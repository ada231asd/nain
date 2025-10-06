"""
Мониторинг статуса станций и уведомления
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from utils.time_utils import get_moscow_time
from utils.centralized_logger import get_logger


class StationStatusMonitor:
    """Мониторинг статуса станций и отправка уведомлений"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('station_status_monitor')
        
        # Кэш статусов станций для отслеживания изменений
        self.station_status_cache: Dict[int, str] = {}
        self.station_last_seen_cache: Dict[int, datetime] = {}
        
        # Настройки мониторинга
        self.offline_threshold = 60  # секунд до считания станции офлайн
        self.heartbeat_interval = 30  # интервал heartbeat
        self.monitor_interval = 10   # интервал проверки статуса
        
        # Очередь запросов для офлайн станций
        self.pending_requests: Dict[int, list] = {}  # station_id -> [requests]
        
    async def start_monitoring(self):
        """Запускает мониторинг станций"""
        self.logger.info("Запуск мониторинга статуса станций")
        
        # Запускаем мониторинг в фоновом режиме
        asyncio.create_task(self._monitor_loop())
        asyncio.create_task(self._process_pending_requests())
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while True:
            try:
                await self._check_station_statuses()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                self.logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(self.monitor_interval)
    
    async def _check_station_statuses(self):
        """Проверяет статус всех станций"""
        try:
            from models.station import Station
            stations = await Station.get_all_active(self.db_pool)
            
            current_time = get_moscow_time()
            
            for station in stations:
                station_id = station.station_id
                old_status = self.station_status_cache.get(station_id, 'unknown')
                old_last_seen = self.station_last_seen_cache.get(station_id)
                
                # Определяем новый статус
                new_status = await self._determine_station_status(station, current_time)
                
                # Обновляем кэш
                self.station_status_cache[station_id] = new_status
                self.station_last_seen_cache[station_id] = station.last_seen
                
                # Проверяем изменения статуса
                if old_status != new_status:
                    await self._handle_status_change(station, old_status, new_status)
                
                # Проверяем, нужно ли обновить статус в БД
                if new_status != station.status:
                    await station.update_status(self.db_pool, new_status)
                    
        except Exception as e:
            self.logger.error(f"Ошибка проверки статуса станций: {e}")
    
    async def _determine_station_status(self, station, current_time: datetime) -> str:
        """Определяет текущий статус станции"""
        try:
            # Проверяем TCP соединение
            connection = self.connection_manager.get_connection_by_station_id(station.station_id)
            has_active_connection = (
                connection and 
                connection.writer and 
                not connection.writer.is_closing()
            )
            
            # Проверяем время последнего контакта
            if station.last_seen:
                time_since_last_seen = (current_time - station.last_seen).total_seconds()
            else:
                time_since_last_seen = float('inf')
            
            # Определяем статус (используем короткие значения для совместимости с БД)
            if station.status == 'pending':
                return 'pending'
            elif station.status == 'maintenance':
                return 'maintenance'
            elif station.status == 'blocked':
                return 'blocked'
            elif has_active_connection and time_since_last_seen <= self.offline_threshold:
                return 'active'
            elif time_since_last_seen <= self.offline_threshold * 2:  # 2 минуты
                return 'inactive'  # Используем 'inactive' вместо 'offline'
            else:
                return 'inactive'  # Используем 'inactive' вместо 'offline'
                
        except Exception as e:
            self.logger.error(f"Ошибка определения статуса станции {station.station_id}: {e}")
            return 'inactive'  # Используем 'inactive' вместо 'offline'
    
    async def _handle_status_change(self, station, old_status: str, new_status: str):
        """Обрабатывает изменение статуса станции"""
        try:
            # Преобразуем статусы для логирования и уведомлений
            display_old_status = self._get_display_status(old_status)
            display_new_status = self._get_display_status(new_status)
            
            self.logger.info(f"Изменение статуса станции {station.box_id}: {display_old_status} -> {display_new_status}")
            
            # Отправляем уведомление на фронтенд с отображаемыми статусами
            await self._notify_status_change(station, display_old_status, display_new_status)
            
            # Если станция стала активной, обрабатываем отложенные запросы
            if new_status == 'active' and old_status in ['inactive', 'pending']:
                await self._process_station_requests(station.station_id)
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки изменения статуса: {e}")
    
    def _get_display_status(self, status: str) -> str:
        """Преобразует внутренний статус в отображаемый"""
        status_map = {
            'inactive': 'offline',
            'active': 'active',
            'pending': 'pending',
            'maintenance': 'maintenance',
            'blocked': 'blocked'
        }
        return status_map.get(status, status)
    
    async def _notify_status_change(self, station, old_status: str, new_status: str):
        """Отправляет уведомление об изменении статуса на фронтенд"""
        try:
            self.logger.info(f"Уведомление: Станция {station.box_id} изменила статус с {old_status} на {new_status}")
            
            # Отправляем WebSocket уведомления
            from api.websocket_endpoints import notify_station_status_change
            
            station_info = {
                'station_id': station.station_id,
                'box_id': station.box_id,
                'status': new_status,
                'last_seen': station.last_seen.isoformat() if station.last_seen else None,
                'slots_declared': station.slots_declared,
                'remain_num': station.remain_num
            }
            
            await notify_station_status_change(
                station.station_id, 
                old_status, 
                new_status, 
                station_info
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления: {e}")
    
    async def add_pending_request(self, station_id: int, request_data: Dict[str, Any]):
        """Добавляет запрос в очередь для офлайн станции"""
        try:
            if station_id not in self.pending_requests:
                self.pending_requests[station_id] = []
            
            request_data['created_at'] = get_moscow_time().isoformat()
            self.pending_requests[station_id].append(request_data)
            
            self.logger.info(f"Добавлен отложенный запрос для станции {station_id}: {request_data.get('type', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления отложенного запроса: {e}")
    
    async def _process_pending_requests(self):
        """Обрабатывает отложенные запросы"""
        while True:
            try:
                # Проверяем каждую станцию с отложенными запросами
                for station_id, requests in list(self.pending_requests.items()):
                    if not requests:
                        continue
                    
                    # Проверяем, активна ли станция
                    connection = self.connection_manager.get_connection_by_station_id(station_id)
                    if connection and connection.writer and not connection.writer.is_closing():
                        # Станция активна, обрабатываем запросы
                        await self._process_station_requests(station_id)
                
                await asyncio.sleep(5)  # Проверяем каждые 5 секунд
                
            except Exception as e:
                self.logger.error(f"Ошибка обработки отложенных запросов: {e}")
                await asyncio.sleep(5)
    
    async def _process_station_requests(self, station_id: int):
        """Обрабатывает запросы для конкретной станции"""
        try:
            if station_id not in self.pending_requests:
                return
            
            requests = self.pending_requests[station_id]
            if not requests:
                return
            
            self.logger.info(f"Обрабатываем {len(requests)} отложенных запросов для станции {station_id}")
            
            # Обрабатываем запросы по очереди
            for request in requests:
                await self._execute_pending_request(station_id, request)
            
            # Очищаем обработанные запросы
            self.pending_requests[station_id] = []
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки запросов станции {station_id}: {e}")
    
    async def _execute_pending_request(self, station_id: int, request: Dict[str, Any]):
        """Выполняет отложенный запрос"""
        try:
            request_type = request.get('type')
            
            if request_type == 'borrow':
                await self._execute_borrow_request(station_id, request)
            elif request_type == 'return':
                await self._execute_return_request(station_id, request)
            elif request_type == 'inventory':
                await self._execute_inventory_request(station_id, request)
            else:
                self.logger.warning(f"Неизвестный тип запроса: {request_type}")
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения отложенного запроса: {e}")
    
    async def _execute_borrow_request(self, station_id: int, request: Dict[str, Any]):
        """Выполняет отложенный запрос на выдачу"""
        # TODO: Реализовать выполнение отложенной выдачи
        self.logger.info(f"Выполняем отложенную выдачу для станции {station_id}")
    
    async def _execute_return_request(self, station_id: int, request: Dict[str, Any]):
        """Выполняет отложенный запрос на возврат"""
        # TODO: Реализовать выполнение отложенного возврата
        self.logger.info(f"Выполняем отложенный возврат для станции {station_id}")
    
    async def _execute_inventory_request(self, station_id: int, request: Dict[str, Any]):
        """Выполняет отложенный запрос инвентаря"""
        # TODO: Реализовать выполнение отложенного запроса инвентаря
        self.logger.info(f"Выполняем отложенный запрос инвентаря для станции {station_id}")
    
    def get_station_status(self, station_id: int) -> str:
        """Получает текущий статус станции"""
        return self.station_status_cache.get(station_id, 'unknown')
    
    def is_station_online(self, station_id: int) -> bool:
        """Проверяет, онлайн ли станция"""
        return self.get_station_status(station_id) == 'active'
    
    def get_display_status(self, station_id: int) -> str:
        """Получает отображаемый статус станции"""
        internal_status = self.get_station_status(station_id)
        return self._get_display_status(internal_status)
    
    def get_pending_requests_count(self, station_id: int) -> int:
        """Получает количество отложенных запросов для станции"""
        return len(self.pending_requests.get(station_id, []))