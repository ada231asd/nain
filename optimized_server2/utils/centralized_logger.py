"""
Централизованная система логирования
Использует единый логгер для всех компонентов
"""
from utils.unified_logger import (
    get_logger, 
    log_tcp_packet, 
    close_logger, 
    get_logger_stats,
    get_unified_logger,
    log_error
)

# Экспортируем функции из единого логгера
__all__ = ['get_logger', 'log_tcp_packet', 'close_logger', 'get_logger_stats', 'log_error']
