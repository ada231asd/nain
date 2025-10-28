"""
Единый централизованный логгер для всего сервера
Перехватывает все логи и записывает в файл с ротацией по дате
Логи хранятся 1 месяц, старые автоматически удаляются
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config.settings import LOG_LEVEL
from logging.handlers import TimedRotatingFileHandler
import glob


class UnifiedLogger:
    """Единый логгер для всего сервера с ротацией по дате"""
    
    def __init__(self):
        self.log_dir = "logs"
        self.log_retention_days = 30  # Хранить логи 1 месяц (30 дней)
        self._original_loggers = {}
        self._file_handler = None
        self._console_handler = None
        self.setup_logging()
        
    def _get_current_log_file(self):
        """Возвращает имя файла лога с текущей датой"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        return f"server_{current_date}.log"
        
    def setup_logging(self):
        """Настраивает единую систему логирования с ротацией по дате"""
        # Создаем директорию для логов если её нет
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Настраиваем формат логов
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Создаем файловый обработчик с ротацией по дате
        log_file_path = os.path.join(self.log_dir, self._get_current_log_file())
        
        # Используем TimedRotatingFileHandler для автоматической ротации в полночь
        self._file_handler = TimedRotatingFileHandler(
            log_file_path,
            when='midnight',  # Ротация в полночь
            interval=1,  # Каждый день
            backupCount=self.log_retention_days,  # Хранить N дней
            encoding='utf-8',
            utc=False  # Использовать локальное время
        )
        self._file_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Настраиваем формат имени для ротированных файлов
        self._file_handler.suffix = "%Y-%m-%d"
        self._file_handler.namer = lambda name: name.replace(".log.", "_") + ".log"
        
        # Создаем консольный обработчик
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
        root_logger.addHandler(self._file_handler)
        root_logger.addHandler(self._console_handler)
        
        # Отключаем все существующие обработчики
        for handler in root_logger.handlers[:]:
            if handler not in [self._file_handler, self._console_handler]:
                root_logger.removeHandler(handler)
        
        # Перехватываем все существующие логгеры
        self._intercept_existing_loggers()
        
        # Очищаем старые логи при старте
        self._cleanup_old_logs()
        
    def _intercept_existing_loggers(self):
        """Перехватывает все существующие логгеры"""
        # Получаем все существующие логгеры
        existing_loggers = list(logging.Logger.manager.loggerDict.keys())
        
        for logger_name in existing_loggers:
            logger = logging.getLogger(logger_name)
            
            # Сохраняем оригинальные обработчики
            self._original_loggers[logger_name] = logger.handlers.copy()
            
            # Очищаем все обработчики
            logger.handlers.clear()
            
            # Устанавливаем propagate=True чтобы логи шли в корневой логгер
            logger.propagate = True
            
    def get_logger(self, name: str) -> logging.Logger:
        """Получает логгер с указанным именем"""
        logger = logging.getLogger(name)
        
        # Убеждаемся что логгер настроен правильно
        if logger not in self._original_loggers:
            self._original_loggers[name] = []
            logger.handlers.clear()
            logger.propagate = True
            
        return logger
        
    def log_tcp_packet(self, packet_type: str = None, data: bytes = None, station_id: str = None, 
                      direction: str = None, packet_size: int = None, command: str = None, 
                      packet_data: str = None, additional_info: str = None):
        """Логирует TCP пакет в единый лог"""
        logger = self.get_logger('tcp_packets')
        from utils.time_utils import format_moscow_time_with_microseconds
        timestamp = format_moscow_time_with_microseconds()
        
        # Формируем сообщение в зависимости от переданных параметров
        if data is not None:
            # Новый формат с bytes
            hex_data = data.hex().upper()
            if station_id:
                logger.info(f"[TCP] [{timestamp}] Station {station_id} - {packet_type}: {hex_data}")
            else:
                logger.info(f"[TCP] [{timestamp}] {packet_type}: {hex_data}")
        else:
            # Старый формат с отдельными параметрами
            parts = []
            if direction:
                parts.append(f"Direction: {direction}")
            if packet_type:
                parts.append(f"Type: {packet_type}")
            if station_id:
                parts.append(f"Station: {station_id}")
            if packet_size:
                parts.append(f"Size: {packet_size}")
            if command:
                parts.append(f"Command: {command}")
            if packet_data:
                parts.append(f"Data: {packet_data}")
            if additional_info:
                parts.append(f"Info: {additional_info}")
                
            message = " | ".join(parts)
            logger.info(f"[TCP] [{timestamp}] {message}")
            
    def log_server_event(self, event_type: str, message: str, **kwargs):
        """Логирует событие сервера"""
        logger = self.get_logger('server_events')
        logger.info(f"[SERVER] {event_type}: {message}")
        
        # Дополнительные параметры
        for key, value in kwargs.items():
            logger.info(f"[SERVER] {event_type} - {key}: {value}")
            
    def log_api_request(self, method: str, endpoint: str, user_id: str = None, **kwargs):
        """Логирует API запрос"""
        logger = self.get_logger('api_requests')
        user_info = f" (user: {user_id})" if user_id else ""
        logger.info(f"[API] {method} {endpoint}{user_info}")
        
        # Дополнительные параметры
        for key, value in kwargs.items():
            logger.info(f"[API] {method} {endpoint} - {key}: {value}")
            
    def log_database_operation(self, operation: str, table: str, **kwargs):
        """Логирует операцию с базой данных"""
        logger = self.get_logger('database')
        logger.info(f"[DB] {operation} on {table}")
        
        # Дополнительные параметры
        for key, value in kwargs.items():
            logger.info(f"[DB] {operation} on {table} - {key}: {value}")
            
    def log_error(self, error_type: str, message: str, exc_info: bool = False, **kwargs):
        """Логирует ошибку"""
        logger = self.get_logger('errors')
        logger.error(f"[ERROR] {error_type}: {message}", exc_info=exc_info)
        
        # Дополнительные параметры
        for key, value in kwargs.items():
            logger.error(f"[ERROR] {error_type} - {key}: {value}")
            
    def log_security_event(self, event_type: str, message: str, **kwargs):
        """Логирует событие безопасности"""
        logger = self.get_logger('security')
        logger.warning(f"[SECURITY] {event_type}: {message}")
        
        # Дополнительные параметры
        for key, value in kwargs.items():
            logger.warning(f"[SECURITY] {event_type} - {key}: {value}")
            
    def _cleanup_old_logs(self):
        """Удаляет логи старше retention_days дней"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=self.log_retention_days)
            
            # Находим все файлы логов
            log_pattern = os.path.join(self.log_dir, "server_*.log")
            log_files = glob.glob(log_pattern)
            
            deleted_count = 0
            for log_file in log_files:
                try:
                    # Получаем время модификации файла
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    
                    # Если файл старше cutoff_time, удаляем его
                    if file_mtime < cutoff_time:
                        os.remove(log_file)
                        deleted_count += 1
                        print(f"Удален старый лог файл: {log_file}")
                except Exception as e:
                    print(f"Ошибка при удалении лог файла {log_file}: {e}")
            
            if deleted_count > 0:
                print(f"Очищено {deleted_count} старых лог файлов (старше {self.log_retention_days} дней)")
                
        except Exception as e:
            print(f"Ошибка при очистке старых логов: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Возвращает статистику логгера"""
        # Подсчитываем количество лог файлов
        log_pattern = os.path.join(self.log_dir, "server_*.log")
        log_files = glob.glob(log_pattern)
        
        # Вычисляем общий размер логов
        total_size = sum(os.path.getsize(f) for f in log_files if os.path.exists(f))
        
        return {
            "current_log_file": self._get_current_log_file(),
            "log_directory": self.log_dir,
            "log_level": LOG_LEVEL,
            "retention_days": self.log_retention_days,
            "total_log_files": len(log_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_loggers": len(logging.Logger.manager.loggerDict),
            "intercepted_loggers": len(self._original_loggers)
        }
        
    def close(self):
        """Закрывает логгер"""
        if self._file_handler:
            self._file_handler.close()
        if self._console_handler:
            self._console_handler.close()
        logging.shutdown()


# Глобальный экземпляр единого логгера
_unified_logger = None

def get_unified_logger() -> UnifiedLogger:
    """Получает глобальный экземпляр единого логгера"""
    global _unified_logger
    if _unified_logger is None:
        _unified_logger = UnifiedLogger()
    return _unified_logger

def get_logger(name: str) -> logging.Logger:
    """Получает логгер через единую систему"""
    return get_unified_logger().get_logger(name)

def log_tcp_packet(packet_type: str = None, data: bytes = None, station_id: str = None, 
                  direction: str = None, packet_size: int = None, command: str = None, 
                  packet_data: str = None, additional_info: str = None):
    """Логирует TCP пакет"""
    get_unified_logger().log_tcp_packet(
        packet_type=packet_type, data=data, station_id=station_id,
        direction=direction, packet_size=packet_size, command=command,
        packet_data=packet_data, additional_info=additional_info
    )

def log_server_event(event_type: str, message: str, **kwargs):
    """Логирует событие сервера"""
    get_unified_logger().log_server_event(event_type, message, **kwargs)

def log_api_request(method: str, endpoint: str, user_id: str = None, **kwargs):
    """Логирует API запрос"""
    get_unified_logger().log_api_request(method, endpoint, user_id, **kwargs)

def log_database_operation(operation: str, table: str, **kwargs):
    """Логирует операцию с базой данных"""
    get_unified_logger().log_database_operation(operation, table, **kwargs)

def log_error(error_type: str, message: str, exc_info: bool = False, **kwargs):
    """Логирует ошибку"""
    get_unified_logger().log_error(error_type, message, exc_info, **kwargs)

def log_security_event(event_type: str, message: str, **kwargs):
    """Логирует событие безопасности"""
    get_unified_logger().log_security_event(event_type, message, **kwargs)

def close_logger():
    """Закрывает единый логгер"""
    global _unified_logger
    if _unified_logger:
        _unified_logger.close()
        _unified_logger = None

def get_logger_stats() -> Dict[str, Any]:
    """Возвращает статистику логгера"""
    return get_unified_logger().get_log_stats()


# Инициализируем единый логгер при импорте модуля
get_unified_logger()
