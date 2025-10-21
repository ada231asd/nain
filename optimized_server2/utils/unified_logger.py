"""
Единый централизованный логгер для всего сервера
Перехватывает все логи и записывает в один файл
"""
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from config.settings import LOG_LEVEL


class UnifiedLogger:
    """Единый логгер для всего сервера"""
    
    def __init__(self):
        self.log_file = "server.log"  # Единственный файл лога
        self._original_loggers = {}
        self.setup_logging()
        
    def setup_logging(self):
        """Настраивает единую систему логирования"""
        # Создаем директорию для логов если её нет
        os.makedirs('logs', exist_ok=True)
        
        # Настраиваем формат логов
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Создаем единый файловый обработчик
        file_handler = logging.FileHandler(f'logs/{self.log_file}', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Создаем консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Отключаем все существующие обработчики
        for handler in root_logger.handlers[:]:
            if handler not in [file_handler, console_handler]:
                root_logger.removeHandler(handler)
        
        # Перехватываем все существующие логгеры
        self._intercept_existing_loggers()
        
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
        
    def log_tcp_packet(self, packet_type: str, data: bytes, station_id: str = None):
        """Логирует TCP пакет в единый лог"""
        logger = self.get_logger('tcp_packets')
        from utils.time_utils import format_moscow_time_with_microseconds
        timestamp = format_moscow_time_with_microseconds()
        
        if station_id:
            logger.info(f"[TCP] [{timestamp}] Station {station_id} - {packet_type}: {data.hex().upper()}")
        else:
            logger.info(f"[TCP] [{timestamp}] {packet_type}: {data.hex().upper()}")
            
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
            
    def get_log_stats(self) -> Dict[str, Any]:
        """Возвращает статистику логгера"""
        return {
            "log_file": f"logs/{self.log_file}",
            "log_level": LOG_LEVEL,
            "total_loggers": len(logging.Logger.manager.loggerDict),
            "intercepted_loggers": len(self._original_loggers)
        }
        
    def close(self):
        """Закрывает логгер"""
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

def log_tcp_packet(packet_type: str, data: bytes, station_id: str = None):
    """Логирует TCP пакет"""
    get_unified_logger().log_tcp_packet(packet_type, data, station_id)

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
