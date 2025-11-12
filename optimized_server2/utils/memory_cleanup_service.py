"""
Сервис периодической очистки памяти для предотвращения утечек
"""
import asyncio
import gc
from typing import Optional, Dict, Any
from utils.centralized_logger import get_logger


class MemoryCleanupService:
    """Централизованный сервис очистки памяти"""
    
    def __init__(self, server_instance=None):
        self.server_instance = server_instance
        self.logger = get_logger('memory_cleanup')
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.cleanup_interval_seconds = 300  # 5 минут по умолчанию
        self.stats = {
            'total_cleanups': 0,
            'last_cleanup_time': None,
            'memory_freed_mb': 0.0
        }
    
    async def start(self, interval_seconds: int = 300):
        """Запускает периодическую очистку памяти"""
        if self._running:
            return
        
        self.cleanup_interval_seconds = interval_seconds
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        self.logger.info(f"Сервис очистки памяти запущен (интервал: {interval_seconds} сек)")
    
    async def stop(self):
        """Останавливает сервис очистки памяти"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("Сервис очистки памяти остановлен")
    
    async def _cleanup_loop(self):
        """Основной цикл очистки памяти"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                if self._running:
                    await self.cleanup_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в цикле очистки памяти: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед повтором
    
    async def cleanup_all(self) -> Dict[str, Any]:
        """Выполняет полную очистку всех кэшей и временных данных"""
        import psutil
        import os
        from datetime import datetime
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        cleanup_results = {
            'timestamp': datetime.now().isoformat(),
            'cleanups': {}
        }
        
        try:
            # 1. Очистка кэшей PowerbankStatusMonitor
            if self.server_instance and self.server_instance.station_handler:
                if hasattr(self.server_instance.station_handler, 'status_monitor'):
                    try:
                        self.server_instance.station_handler.status_monitor.cleanup_cache()
                        cleanup_results['cleanups']['powerbank_status_monitor'] = 'success'
                    except Exception as e:
                        self.logger.error(f"Ошибка очистки PowerbankStatusMonitor: {e}")
                        cleanup_results['cleanups']['powerbank_status_monitor'] = f'error: {e}'
            
            # 2. Очистка кэша PowerbankReminderService
            if self.server_instance and hasattr(self.server_instance, 'reminder_service'):
                if self.server_instance.reminder_service:
                    try:
                        # Очистка уже происходит внутри сервиса, но можно принудительно
                        if len(self.server_instance.reminder_service.sent_reminders) > self.server_instance.reminder_service.max_reminders_cache:
                            items_to_remove = len(self.server_instance.reminder_service.sent_reminders) - int(
                                self.server_instance.reminder_service.max_reminders_cache * 0.8
                            )
                            reminders_list = list(self.server_instance.reminder_service.sent_reminders)
                            for item in reminders_list[:items_to_remove]:
                                self.server_instance.reminder_service.sent_reminders.discard(item)
                        cleanup_results['cleanups']['powerbank_reminder_service'] = 'success'
                    except Exception as e:
                        self.logger.error(f"Ошибка очистки PowerbankReminderService: {e}")
                        cleanup_results['cleanups']['powerbank_reminder_service'] = f'error: {e}'
            
            # 3. Очистка неактивных соединений (уже есть в ConnectionManager)
            if self.server_instance and self.server_instance.connection_manager:
                try:
                    cleaned = self.server_instance.connection_manager.cleanup_inactive_connections(120)
                    cleanup_results['cleanups']['connection_manager'] = f'cleaned {cleaned} connections'
                except Exception as e:
                    self.logger.error(f"Ошибка очистки ConnectionManager: {e}")
                    cleanup_results['cleanups']['connection_manager'] = f'error: {e}'
            
            # 4. Принудительный вызов Python GC
            try:
                collected = gc.collect()
                cleanup_results['cleanups']['python_gc'] = f'collected {collected} objects'
            except Exception as e:
                self.logger.error(f"Ошибка Python GC: {e}")
                cleanup_results['cleanups']['python_gc'] = f'error: {e}'
            
            # 5. Очистка WebSocket соединений (если есть)
            if self.server_instance and self.server_instance.http_server:
                try:
                    if hasattr(self.server_instance.http_server, 'user_notification_manager'):
                        manager = self.server_instance.http_server.user_notification_manager
                        if manager:
                            # Очищаем закрытые WebSocket соединения
                            closed_connections = []
                            for user_id, ws in list(manager.user_connections.items()):
                                if ws.closed:
                                    closed_connections.append(user_id)
                            
                            for user_id in closed_connections:
                                manager.unregister_user(user_id)
                            
                            cleanup_results['cleanups']['websocket_connections'] = f'cleaned {len(closed_connections)} closed connections'
                except Exception as e:
                    self.logger.error(f"Ошибка очистки WebSocket соединений: {e}")
                    cleanup_results['cleanups']['websocket_connections'] = f'error: {e}'
            
            # Вычисляем освобожденную память
            memory_after = process.memory_info().rss / (1024 * 1024)  # MB
            memory_freed = memory_before - memory_after
            
            cleanup_results['memory_before_mb'] = round(memory_before, 2)
            cleanup_results['memory_after_mb'] = round(memory_after, 2)
            cleanup_results['memory_freed_mb'] = round(memory_freed, 2)
            
            # Обновляем статистику
            self.stats['total_cleanups'] += 1
            self.stats['last_cleanup_time'] = datetime.now().isoformat()
            self.stats['memory_freed_mb'] += memory_freed
            
            if memory_freed > 0.1:  # Логируем только если освобождено больше 0.1 MB
                self.logger.info(
                    f"Очистка памяти завершена: освобождено {memory_freed:.2f} MB "
                    f"(было: {memory_before:.2f} MB, стало: {memory_after:.2f} MB)"
                )
            
            return cleanup_results
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка при очистке памяти: {e}", exc_info=True)
            cleanup_results['error'] = str(e)
            return cleanup_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику очистки памяти"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        current_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        return {
            **self.stats,
            'current_memory_mb': round(current_memory, 2),
            'cleanup_interval_seconds': self.cleanup_interval_seconds,
            'is_running': self._running
        }


