"""
Утилиты для работы с заказами и защиты от дублирования
"""
from typing import Optional, Tuple
from models.order import Order
from utils.centralized_logger import get_logger


async def check_duplicate_borrow_order(db_pool, user_id: int, powerbank_id: int, 
                                     station_id: int) -> Tuple[bool, str]:
    """
    Проверяет наличие дублирующих заказов на выдачу
    
    Args:
        db_pool: Пул соединений с БД
        user_id: ID пользователя
        powerbank_id: ID powerbank'а
        station_id: ID станции
        
    Returns:
        tuple[bool, str]: (есть_дубликат, сообщение)
    """
    try:
        logger = get_logger('order_utils')
        
        # Проверяем активные заказы пользователя
        active_user_orders = await Order.get_active_orders_by_user(db_pool, user_id)
        if active_user_orders:
            # Проверяем, есть ли заказ на тот же powerbank
            for order in active_user_orders:
                if order.powerbank_id == powerbank_id:
                    logger.warning(f"Дублирующий заказ: пользователь {user_id} уже имеет активный заказ {order.order_id} на powerbank {powerbank_id}")
                    return True, f"У вас уже есть активный заказ на этот powerbank (заказ #{order.order_id})"
        
        # Проверяем активные заказы на powerbank
        active_powerbank_order = await Order.get_active_by_powerbank_id(db_pool, powerbank_id)
        if active_powerbank_order:
            logger.warning(f"Дублирующий заказ: powerbank {powerbank_id} уже выдан в заказе {active_powerbank_order.order_id}")
            return True, f"Powerbank уже выдан другому пользователю (заказ #{active_powerbank_order.order_id})"
        
        logger.info(f"Проверка дубликатов пройдена: пользователь {user_id}, powerbank {powerbank_id}, станция {station_id}")
        return False, "Дубликатов не найдено"
        
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка проверки дубликатов заказов: {e}")
        return True, f"Ошибка проверки дубликатов: {e}"


async def check_powerbank_availability(db_pool, powerbank_id: int) -> Tuple[bool, str]:
    """
    Проверяет доступность powerbank'а для выдачи
    
    Args:
        db_pool: Пул соединений с БД
        powerbank_id: ID powerbank'а
        
    Returns:
        tuple[bool, str]: (доступен, сообщение)
    """
    try:
        from models.powerbank import Powerbank
        from models.station_powerbank import StationPowerbank
        
        logger = get_logger('order_utils')
        
        # Проверяем существование powerbank'а
        powerbank = await Powerbank.get_by_id(db_pool, powerbank_id)
        if not powerbank:
            return False, f"Powerbank {powerbank_id} не найден"
        
        # Проверяем статус powerbank'а
        if powerbank.status != 'active':
            logger.warning(f"Powerbank {powerbank_id} недоступен (статус: {powerbank.status})")
            return False, f"Powerbank недоступен (статус: {powerbank.status})"
        
        # Проверяем, что powerbank находится в станции
        station_powerbank = await StationPowerbank.get_by_powerbank_id(db_pool, powerbank_id)
        if not station_powerbank:
            logger.warning(f"Powerbank {powerbank_id} не найден ни в одной станции")
            return False, "Powerbank не найден в станциях"
        
        # Проверяем активные заказы на powerbank
        active_order = await Order.get_active_by_powerbank_id(db_pool, powerbank_id)
        if active_order:
            logger.warning(f"Powerbank {powerbank_id} уже выдан в заказе {active_order.order_id}")
            return False, f"Powerbank уже выдан (заказ #{active_order.order_id})"
        
        logger.info(f"Powerbank {powerbank_id} ({powerbank.serial_number}) доступен для выдачи")
        return True, f"Powerbank {powerbank.serial_number} доступен"
        
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка проверки доступности powerbank {powerbank_id}: {e}")
        return False, f"Ошибка проверки доступности: {e}"


async def validate_borrow_request(db_pool, user_id: int, powerbank_id: int, 
                                station_id: int) -> Tuple[bool, str]:
    """
    Комплексная валидация запроса на выдачу powerbank'а
    
    """
    try:
        logger = get_logger('order_utils')
        logger.info(f"Валидация запроса на выдачу: пользователь {user_id}, powerbank {powerbank_id}, станция {station_id}")
        
        # Проверяем дубликаты заказов
        has_duplicate, duplicate_message = await check_duplicate_borrow_order(
            db_pool, user_id, powerbank_id, station_id
        )
        if has_duplicate:
            return False, duplicate_message
        
        # Проверяем доступность powerbank'а
        is_available, availability_message = await check_powerbank_availability(
            db_pool, powerbank_id
        )
        if not is_available:
            return False, availability_message
        
        logger.info(f"Валидация запроса на выдачу пройдена успешно")
        return True, "Запрос валиден"
        
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка валидации запроса на выдачу: {e}")
        return False, f"Ошибка валидации: {e}"

