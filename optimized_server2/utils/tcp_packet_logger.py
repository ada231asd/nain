"""
Специализированный логгер для TCP пакетов
Записывает только пакеты от станций и к станциям
"""
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
from config.settings import TCP_PACKETS_LOG, LOG_LEVEL

# Глобальная переменная для TCP логгера
_tcp_logger: Optional[logging.Logger] = None

def get_tcp_logger() -> logging.Logger:
    """Получает или создает TCP логгер"""
    global _tcp_logger
    
    if _tcp_logger is None:
        _tcp_logger = _setup_tcp_logger()
    
    return _tcp_logger

def _setup_tcp_logger() -> logging.Logger:
    """Настраивает TCP логгер"""
    # Создаем директорию для логов если не существует
    os.makedirs(os.path.dirname(TCP_PACKETS_LOG), exist_ok=True)
    
    # Создаем логгер
    logger = logging.getLogger('tcp_packets')
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Создаем файловый обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        TCP_PACKETS_LOG,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Создаем форматтер для TCP пакетов
    formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Добавляем обработчик
    logger.addHandler(file_handler)
    
    # Отключаем распространение в родительские логгеры
    logger.propagate = False
    
    return logger

def log_tcp_packet(direction: str, packet_type: str, station_id: str, 
                  packet_size: int, command: str, packet_data: str, 
                  additional_info: str = "") -> None:
    """
    Логирует TCP пакет
    
    Args:
        direction: "INCOMING" или "OUTGOING"
        packet_type: Тип пакета (Login, Heartbeat, etc.)
        station_id: ID станции
        packet_size: Размер пакета в байтах
        command: Команда (0x64, 0x80, etc.)
        packet_data: Hex данные пакета
        additional_info: Дополнительная информация
    """
    logger = get_tcp_logger()
    
    # Добавляем микросекунды к сообщению
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # Формируем сообщение
    message_parts = [
        f"[{direction}]",
        f"[{packet_type}]",
        f"[{packet_size} bytes]",
        f"[{command}]",
        f"[{packet_data}]",
        f"[{station_id}]"
    ]
    
    if additional_info:
        message_parts.append(f"[{additional_info}]")
    
    message = f"{timestamp} | " + " ".join(message_parts)
    
    # Логируем
    logger.info(message)

def log_tcp_error(station_id: str, error_message: str, packet_data: str = "") -> None:
    """
    Логирует ошибку TCP пакета
    
    Args:
        station_id: ID станции
        error_message: Сообщение об ошибке
        packet_data: Hex данные пакета (опционально)
    """
    logger = get_tcp_logger()
    
    # Добавляем микросекунды к сообщению
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    message_parts = [
        f"[ERROR]",
        f"[{station_id}]",
        f"[{error_message}]"
    ]
    
    if packet_data:
        message_parts.append(f"[{packet_data}]")
    
    message = f"{timestamp} | " + " ".join(message_parts)
    logger.error(message)

def close_tcp_logger() -> None:
    """Закрывает TCP логгер"""
    global _tcp_logger
    
    if _tcp_logger:
        for handler in _tcp_logger.handlers:
            handler.close()
        _tcp_logger = None

def get_tcp_logger_stats() -> dict:
    """Возвращает статистику TCP логгера"""
    global _tcp_logger
    
    if not _tcp_logger:
        return {"handlers": 0, "level": "NOT_SET"}
    
    return {
        "handlers": len(_tcp_logger.handlers),
        "level": _tcp_logger.level,
        "log_file": TCP_PACKETS_LOG
    }
