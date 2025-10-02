"""
Централизованные утилиты для работы с московским временем
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


# Московская временная зона (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_moscow_time() -> datetime:
    """
    Возвращает текущее московское время (UTC+3)
    
    Returns:
        datetime: Текущее время в московской временной зоне
    """
    return datetime.now(MOSCOW_TZ)


def get_moscow_now() -> datetime:
    """
    Алиас для get_moscow_time() для обратной совместимости
    
    Returns:
        datetime: Текущее время в московской временной зоне
    """
    return get_moscow_time()


def moscow_timestamp() -> float:
    """
    Возвращает timestamp московского времени
    
    Returns:
        float: Unix timestamp в московском времени
    """
    return get_moscow_time().timestamp()


def format_moscow_time(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Форматирует московское время в строку
    
    Args:
        dt: Объект datetime (если None, используется текущее время)
        format_str: Формат строки (по умолчанию "%Y-%m-%d %H:%M:%S")
        
    Returns:
        str: Отформатированная строка времени
    """
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        # Если время без временной зоны, считаем его московским
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        # Конвертируем в московское время
        dt = dt.astimezone(MOSCOW_TZ)
    
    return dt.strftime(format_str)


def format_moscow_time_with_microseconds(dt: Optional[datetime] = None) -> str:
    """
    Форматирует московское время с микросекундами для логирования
    
    Args:
        dt: Объект datetime (если None, используется текущее время)
        
    Returns:
        str: Время в формате "YYYY-MM-DD HH:MM:SS.mmm"
    """
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        dt = dt.astimezone(MOSCOW_TZ)
    
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Убираем последние 3 цифры микросекунд


def to_moscow_time(dt: datetime) -> datetime:
    """
    Конвертирует datetime в московское время
    
    Args:
        dt: Объект datetime для конвертации
        
    Returns:
        datetime: Время в московской временной зоне
    """
    if dt.tzinfo is None:
        # Если время без временной зоны, считаем его UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(MOSCOW_TZ)


def from_timestamp_moscow(timestamp: float) -> datetime:
    """
    Создает datetime из timestamp в московском времени
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        datetime: Объект datetime в московской временной зоне
    """
    return datetime.fromtimestamp(timestamp, tz=MOSCOW_TZ)


def is_moscow_timezone(dt: datetime) -> bool:
    """
    Проверяет, находится ли datetime в московской временной зоне
    
    Args:
        dt: Объект datetime для проверки
        
    Returns:
        bool: True если время в московской зоне, False иначе
    """
    return dt.tzinfo == MOSCOW_TZ if dt.tzinfo else False
