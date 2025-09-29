"""
Централизованная система логирования
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from config.settings import LOG_LEVEL


def setup_logging():
    """Настраивает систему логирования"""
    # Создаем директорию для логов если её нет
    os.makedirs('logs', exist_ok=True)
    
    # Настраиваем формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler('logs/app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Настраиваем логгер для TCP пакетов
    tcp_logger = logging.getLogger('tcp_packets')
    tcp_handler = logging.FileHandler('logs/tcp_packets.log', encoding='utf-8')
    tcp_handler.setFormatter(logging.Formatter(log_format, date_format))
    tcp_logger.addHandler(tcp_handler)
    tcp_logger.setLevel(logging.INFO)
    
    # Отключаем дублирование в корневой логгер
    tcp_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Получает логгер с указанным именем"""
    return logging.getLogger(name)


def log_tcp_packet(packet_type: str, data: bytes, station_id: str = None):
    """Логирует TCP пакет"""
    tcp_logger = get_logger('tcp_packets')
    moscow_tz = timezone(timedelta(hours=3))  # UTC+3
    timestamp = datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    if station_id:
        tcp_logger.info(f"[{timestamp}] Station {station_id} - {packet_type}: {data.hex().upper()}")
    else:
        tcp_logger.info(f"[{timestamp}] {packet_type}: {data.hex().upper()}")


def close_logger():
    """Закрывает все логгеры"""
    logging.shutdown()


def get_logger_stats() -> Dict[str, Any]:
    """Возвращает статистику логгеров"""
    return {
        "active_loggers": len(logging.Logger.manager.loggerDict),
        "log_level": LOG_LEVEL
    }


# Инициализируем логирование при импорте модуля
setup_logging()