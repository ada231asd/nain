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
    """
    return datetime.now(MOSCOW_TZ)


def get_moscow_now() -> datetime:
    """
    Алиас для get_moscow_time() для обратной совместимости

    """
    return get_moscow_time()


def moscow_timestamp() -> float:
    """
    Возвращает timestamp московского времени

    """
    return get_moscow_time().timestamp()


def format_moscow_time(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Форматирует московское время в строку

    """
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        dt = dt.astimezone(MOSCOW_TZ)
    
    return dt.strftime(format_str)


def format_moscow_time_with_microseconds(dt: Optional[datetime] = None) -> str:
    """
    Форматирует московское время с микросекундами для логирования

    """
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        dt = dt.astimezone(MOSCOW_TZ)
    
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  


def to_moscow_time(dt: datetime) -> datetime:
    """
    Конвертирует datetime в московское время

    """
    if dt.tzinfo is None:
        # Если время без временной зоны, считаем его UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(MOSCOW_TZ)


def normalize_datetime_to_moscow(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Нормализует datetime объект к московскому времени

    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        return dt.astimezone(MOSCOW_TZ)
    else:
        return dt


def from_timestamp_moscow(timestamp: float) -> datetime:
    """
    Создает datetime из timestamp в московском времени

    """
    return datetime.fromtimestamp(timestamp, tz=MOSCOW_TZ)


def is_moscow_timezone(dt: datetime) -> bool:
    """
    Проверяет, находится ли datetime в московской временной зоне

    """
    return dt.tzinfo == MOSCOW_TZ if dt.tzinfo else False
