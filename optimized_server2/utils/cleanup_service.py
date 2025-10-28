"""
Сервис фоновой очистки данных
- Очистка старых логов (>30 дней)
- Очистка просроченных пригласительных ссылок (>7 дней)
"""
import asyncio
from datetime import datetime, timedelta
import os
import glob
from typing import Optional
from utils.invitation_storage import invitation_storage
from utils.centralized_logger import get_logger


logger = get_logger('cleanup_service')


class CleanupService:
    """Сервис автоматической очистки устаревших данных"""
    
    def __init__(self, log_retention_days: int = 30, invitation_retention_days: int = 7):
        self.log_retention_days = log_retention_days
        self.invitation_retention_days = invitation_retention_days
        self.log_dir = "logs"
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Запускает фоновую задачу очистки"""
        if self._running:
            logger.warning("Сервис очистки уже запущен")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Сервис очистки запущен")
        
    async def stop(self):
        """Останавливает фоновую задачу очистки"""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Сервис очистки остановлен")
        
    async def _cleanup_loop(self):
        """Основной цикл очистки - выполняется каждый день в 3:00"""
        logger.info("Фоновая задача очистки данных запущена")
        
        while self._running:
            try:
                # Вычисляем время до следующего запуска (3:00 следующего дня)
                now = datetime.now()
                next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                
                # Если уже прошло 3:00 сегодня, планируем на завтра
                if now >= next_run:
                    next_run += timedelta(days=1)
                
                sleep_seconds = (next_run - now).total_seconds()
                
                logger.info(f"Следующая очистка запланирована на {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Ожидание {sleep_seconds/3600:.1f} часов до следующей очистки")
                
                # Ждем до времени запуска
                await asyncio.sleep(sleep_seconds)
                
                # Выполняем очистку
                await self._run_cleanup()
                
            except asyncio.CancelledError:
                logger.info("Задача очистки отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле очистки: {e}", exc_info=True)
                # Ждем 1 час перед повторной попыткой
                await asyncio.sleep(3600)
                
    async def _run_cleanup(self):
        """Выполняет все операции очистки"""
        logger.info("=== Начало процедуры очистки данных ===")
        start_time = datetime.now()
        
        # 1. Очистка старых логов
        deleted_logs = await self._cleanup_old_logs()
        
        # 2. Очистка просроченных приглашений
        deleted_invitations = await self._cleanup_expired_invitations()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"=== Очистка завершена за {duration:.2f} секунд ===")
        logger.info(f"Удалено логов: {deleted_logs}")
        logger.info(f"Удалено приглашений: {deleted_invitations}")
        
    async def _cleanup_old_logs(self) -> int:
        """Очищает старые лог файлы"""
        try:
            logger.info(f"Очистка логов старше {self.log_retention_days} дней...")
            
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=self.log_retention_days)
            
            # Находим все файлы логов
            log_pattern = os.path.join(self.log_dir, "server_*.log")
            log_files = glob.glob(log_pattern)
            
            deleted_count = 0
            total_size_deleted = 0
            
            for log_file in log_files:
                try:
                    # Получаем время модификации файла
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    
                    # Если файл старше cutoff_time, удаляем его
                    if file_mtime < cutoff_time:
                        file_size = os.path.getsize(log_file)
                        os.remove(log_file)
                        deleted_count += 1
                        total_size_deleted += file_size
                        logger.info(f"Удален старый лог файл: {log_file} ({file_size/1024:.2f} KB)")
                except Exception as e:
                    logger.error(f"Ошибка при удалении лог файла {log_file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Удалено {deleted_count} лог файлов, освобождено {total_size_deleted/1024/1024:.2f} MB")
            else:
                logger.info("Нет логов для удаления")
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых логов: {e}", exc_info=True)
            return 0
    
    async def _cleanup_expired_invitations(self) -> int:
        """Очищает просроченные пригласительные ссылки"""
        try:
            logger.info(f"Очистка пригласительных ссылок старше {self.invitation_retention_days} дней...")
            
            # Получаем все приглашения
            all_invitations = invitation_storage.get_all_invitations()
            initial_count = len(all_invitations)
            
            # _cleanup_expired() внутри get_all_invitations() уже удаляет устаревшие
            # Но мы вызываем принудительно для логирования
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=self.invitation_retention_days)
            
            expired_tokens = []
            for invitation in all_invitations:
                created_at = datetime.fromisoformat(invitation['created_at'])
                if created_at < cutoff_time:
                    expired_tokens.append(invitation['token'])
            
            # Удаляем вручную для подсчета
            for token in expired_tokens:
                if token in invitation_storage.invitations:
                    del invitation_storage.invitations[token]
            
            if expired_tokens:
                invitation_storage._save_to_file()
                logger.info(f"Удалено {len(expired_tokens)} просроченных приглашений")
            else:
                logger.info("Нет просроченных приглашений для удаления")
            
            return len(expired_tokens)
            
        except Exception as e:
            logger.error(f"Ошибка при очистке приглашений: {e}", exc_info=True)
            return 0
    
    async def force_cleanup(self):
        """Принудительный запуск очистки (для тестирования или ручного запуска)"""
        logger.info("Запущена принудительная очистка")
        await self._run_cleanup()
    
    def get_status(self) -> dict:
        """Возвращает статус сервиса очистки"""
        return {
            "running": self._running,
            "log_retention_days": self.log_retention_days,
            "invitation_retention_days": self.invitation_retention_days,
            "log_directory": self.log_dir
        }


# Глобальный экземпляр сервиса очистки
cleanup_service = CleanupService()

