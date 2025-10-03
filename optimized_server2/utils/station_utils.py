"""
Утилиты для работы со станциями
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from models.station import Station
from utils.time_utils import get_moscow_time
from utils.centralized_logger import get_logger


async def check_station_online_status(db_pool, station_id: int, required_seconds: int = 30) -> Tuple[bool, str]:
    """
    Проверяет, была ли станция онлайн в течение указанного количества секунд
    
    Args:
        db_pool: Пул соединений с БД
        station_id: ID станции
        required_seconds: Количество секунд для проверки (по умолчанию 30)
        
    Returns:
        tuple[bool, str]: (статус_онлайн, сообщение)
    """
    try:
        logger = get_logger('station_utils')
        
        # Получаем информацию о станции
        station = await Station.get_by_id(db_pool, station_id)
        if not station:
            return False, f"Станция {station_id} не найдена"
        
        # Проверяем статус станции
        if station.status != 'active':
            return False, f"Станция {station.box_id} неактивна (статус: {station.status})"
        
        # Проверяем время последнего подключения
        if not station.last_seen:
            return False, f"Станция {station.box_id} никогда не подключалась"
        
        current_time = get_moscow_time()
        
        # Нормализуем last_seen к московскому времени
        from utils.time_utils import normalize_datetime_to_moscow
        last_seen = normalize_datetime_to_moscow(station.last_seen)
        
        time_diff = current_time - last_seen
        
        if time_diff.total_seconds() > required_seconds:
            logger.warning(f"Станция {station.box_id} была офлайн {int(time_diff.total_seconds())} секунд (требуется не более {required_seconds})")
            return False, f"Станция {station.box_id} была офлайн {int(time_diff.total_seconds())} секунд назад. Для безопасности операции разрешены только если станция была онлайн не более {required_seconds} секунд назад."
        
        logger.info(f"Станция {station.box_id} онлайн (последнее подключение: {int(time_diff.total_seconds())} секунд назад)")
        return True, f"Станция {station.box_id} онлайн"
        
    except Exception as e:
        logger = get_logger('station_utils')
        logger.error(f"Ошибка проверки статуса станции {station_id}: {e}")
        return False, f"Ошибка проверки статуса станции: {e}"


async def check_station_connection_status(connection_manager, station_id: int) -> Tuple[bool, str]:
    """
    Проверяет активное TCP соединение со станцией
    
    Args:
        connection_manager: Менеджер соединений
        station_id: ID станции
        
    Returns:
        tuple[bool, str]: (соединение_активно, сообщение)
    """
    try:
        if not connection_manager:
            return False, "Connection manager недоступен"
        
        connection = connection_manager.get_connection_by_station_id(station_id)
        if not connection:
            return False, f"TCP соединение со станцией {station_id} отсутствует"
        
        if not connection.writer or connection.writer.is_closing():
            return False, f"TCP соединение со станцией {station_id} закрыто"
        
        return True, f"TCP соединение со станцией {station_id} активно"
        
    except Exception as e:
        logger = get_logger('station_utils')
        logger.error(f"Ошибка проверки соединения со станцией {station_id}: {e}")
        return False, f"Ошибка проверки соединения: {e}"


async def validate_station_for_operation(db_pool, connection_manager, station_id: int, 
                                       operation_name: str = "операция", 
                                       required_online_seconds: int = 30) -> Tuple[bool, str]:
    """
    Комплексная проверка станции перед выполнением операции
    
    Args:
        db_pool: Пул соединений с БД
        connection_manager: Менеджер соединений
        station_id: ID станции
        operation_name: Название операции для логирования
        required_online_seconds: Требуемое время онлайн в секундах
        
    Returns:
        tuple[bool, str]: (можно_выполнять_операцию, сообщение)
    """
    try:
        logger = get_logger('station_utils')
        logger.info(f"Проверка станции {station_id} перед операцией '{operation_name}'")
        
        # Проверяем статус онлайн по базе данных
        online_status, online_message = await check_station_online_status(
            db_pool, station_id, required_online_seconds
        )
        
        if not online_status:
            logger.warning(f"Станция {station_id} не прошла проверку онлайн статуса: {online_message}")
            return False, online_message
        
        # Проверяем активное TCP соединение
        connection_status, connection_message = await check_station_connection_status(
            connection_manager, station_id
        )
        
        if not connection_status:
            logger.warning(f"Станция {station_id} не прошла проверку TCP соединения: {connection_message}")
            return False, connection_message
        
        logger.info(f"Станция {station_id} прошла все проверки для операции '{operation_name}'")
        return True, f"Станция готова к выполнению операции '{operation_name}'"
        
    except Exception as e:
        logger = get_logger('station_utils')
        logger.error(f"Ошибка валидации станции {station_id} для операции '{operation_name}': {e}")
        return False, f"Ошибка валидации станции: {e}"

