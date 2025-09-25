"""
TCP пакет логгер - использует основной логгер для минимизации файловых дескрипторов
"""
from utils.centralized_logger import get_logger

def get_tcp_logger():
    """Возвращает основной логгер для TCP пакетов"""
    return get_logger('tcp_packets')

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
    """Закрывает TCP логгер (теперь не нужно - используется основной)"""
    pass  # TCP логгер теперь использует основной логгер

def get_tcp_logger_stats() -> dict:
    """Возвращает статистику TCP логгера"""
    from utils.centralized_logger import get_logger_stats
    stats = get_logger_stats()
    return {
        "handlers": stats["handlers"],
        "file_descriptors": stats["file_descriptors"],
        "log_file": "logs/server.log"  # Теперь все в одном файле
    }
