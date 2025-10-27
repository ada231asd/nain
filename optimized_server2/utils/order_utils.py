"""
Утилиты для работы с заказами и защиты от дублирования
"""
from typing import Optional, Tuple, Dict, Any
from models.order import Order
from utils.centralized_logger import get_logger


async def check_duplicate_borrow_order(db_pool, user_id: int, powerbank_id: int, 
                                     station_id: int) -> Tuple[bool, str]:
    """
    Проверяет наличие дублирующих заказов на выдачу
    
    """
    try:
        logger = get_logger('order_utils')
        
        # Получаем телефон пользователя и серийный номер powerbank'а
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Получаем телефон пользователя
                await cur.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_result = await cur.fetchone()
                if not user_result:
                    return True, "Пользователь не найден"
                user_phone = user_result[0]
                
                # Получаем серийный номер powerbank'а
                await cur.execute("""
                    SELECT serial_number FROM powerbank WHERE id = %s
                """, (powerbank_id,))
                powerbank_result = await cur.fetchone()
                if not powerbank_result:
                    return True, "Powerbank не найден"
                powerbank_serial = powerbank_result[0]
        
        # Проверяем активные заказы пользователя
        active_user_orders = await Order.get_active_by_user_phone(db_pool, user_phone)
        if active_user_orders:
            # Проверяем, есть ли заказ на тот же powerbank
            for order in active_user_orders:
                if order.powerbank_serial == powerbank_serial:
                    logger.warning(f"Дублирующий заказ: пользователь {user_id} уже имеет активный заказ {order.order_id} на powerbank {powerbank_serial}")
                    return True, f"У вас уже есть активный заказ на этот powerbank (заказ #{order.order_id})"
        
        # Проверяем активные заказы на powerbank
        active_powerbank_order = await Order.get_active_by_powerbank_serial(db_pool, powerbank_serial)
        if active_powerbank_order:
            logger.warning(f"Дублирующий заказ: powerbank {powerbank_serial} уже выдан в заказе {active_powerbank_order.order_id}")
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
        
        # Получаем серийный номер powerbank'а для поиска в orders
        powerbank_serial = powerbank.serial_number if powerbank else None
        if not powerbank_serial:
            return False, "Серийный номер powerbank'а не найден"
        
        # Проверяем активные заказы на powerbank
        active_order = await Order.get_active_by_powerbank_serial(db_pool, powerbank_serial)
        if active_order:
            logger.warning(f"Powerbank {powerbank_serial} уже выдан в заказе {active_order.order_id}")
            return False, f"Powerbank уже выдан (заказ #{active_order.order_id})"
        
        logger.info(f"Powerbank {powerbank_id} ({powerbank.serial_number}) доступен для выдачи")
        return True, f"Powerbank {powerbank.serial_number} доступен"
        
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка проверки доступности powerbank {powerbank_id}: {e}")
        return False, f"Ошибка проверки доступности: {e}"


async def check_user_powerbank_limit(db_pool, user_id: int) -> Tuple[bool, str]:
    """
    Проверяет, не превышен ли лимит повербанков для пользователя
    
    """
    try:
        logger = get_logger('order_utils')
        
        # Получаем информацию о пользователе с лимитами
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Проверяем роль пользователя: администраторы не ограничены лимитом
                await cur.execute(
                    """
                    SELECT COALESCE(ur.role, 'user') as role
                    FROM app_user au
                    LEFT JOIN user_role ur ON au.user_id = ur.user_id
                    WHERE au.user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                role_row = await cur.fetchone()
                role = role_row[0] if role_row else 'user'
                if role in ('service_admin', 'group_admin', 'subgroup_admin'):
                    return True, f"Лимит не применяется для роли: {role}"

                await cur.execute("""
                    SELECT 
                        au.user_id,
                        au.powerbank_limit as individual_limit,
                        ou.default_powerbank_limit as group_default_limit,
                        ou.name as group_name,
                        CASE 
                            WHEN au.powerbank_limit IS NOT NULL THEN au.powerbank_limit
                            WHEN ou.default_powerbank_limit IS NOT NULL THEN ou.default_powerbank_limit
                            ELSE 0
                        END as effective_limit,
                        CASE 
                            WHEN au.powerbank_limit IS NOT NULL THEN 'individual'
                            WHEN ou.default_powerbank_limit IS NOT NULL THEN 'group'
                            ELSE 'no_group'
                        END as limit_type
                    FROM app_user au
                    LEFT JOIN user_role ur ON au.user_id = ur.user_id
                    LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                    WHERE au.user_id = %s
                """, (user_id,))
                
                user_data = await cur.fetchone()
                
                if not user_data:
                    return False, "Пользователь не найден"
                
                effective_limit = user_data[4]  # effective_limit
                limit_type = user_data[5]       # limit_type
                
                # Если лимит = 0 (пользователь не в группе), запрещаем выдачу
                if effective_limit == 0:
                    return False, "Пользователь не привязан к группе и не может брать повербанки"
                
                # Получаем телефон пользователя для поиска в orders
                await cur.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                phone_result = await cur.fetchone()
                if not phone_result:
                    return False, "Пользователь не найден"
                user_phone = phone_result[0]
                
                # Подсчитываем количество активных повербанков у пользователя
                await cur.execute("""
                    SELECT COUNT(*) as active_count
                    FROM orders o
                    WHERE o.user_phone = %s 
                    AND o.status = 'borrow' 
                    AND o.completed_at IS NULL
                """, (user_phone,))
                
                active_count_result = await cur.fetchone()
                active_count = active_count_result[0] if active_count_result else 0
                
                # Проверяем, не превышен ли лимит
                if active_count >= effective_limit:
                    limit_source = "индивидуального лимита" if limit_type == 'individual' else f"лимита группы"
                    return False, f"Превышен лимит повербанков ({active_count}/{effective_limit}). Источник: {limit_source}"
                
                logger.info(f"Пользователь {user_id}: активных повербанков {active_count}/{effective_limit} (тип: {limit_type})")
                return True, f"Лимит не превышен ({active_count}/{effective_limit})"
                
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка проверки лимита пользователя {user_id}: {e}")
        return False, f"Ошибка проверки лимита: {e}"


async def get_user_limit_info(db_pool, user_id: int) -> Dict[str, Any]:
    """
    Возвращает подробную информацию о лимите пользователя:
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Проверяем роль: для админов показываем, что лимит отключён
                await cur.execute(
                    """
                    SELECT COALESCE(ur.role, 'user') as role
                    FROM app_user au
                    LEFT JOIN user_role ur ON au.user_id = ur.user_id
                    WHERE au.user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                role_row = await cur.fetchone()
                role = role_row[0] if role_row else 'user'
                if role in ('service_admin', 'group_admin', 'subgroup_admin'):
                    return {
                        "user_id": user_id,
                        "individual_limit": None,
                        "group_default_limit": None,
                        "group_name": None,
                        "effective_limit": None,
                        "limit_type": "role_exempt",
                        "role": role,
                        "active_count": await _get_active_count(conn, user_id),
                    }
                await cur.execute(
                    """
                    SELECT 
                        au.user_id,
                        au.powerbank_limit as individual_limit,
                        ou.default_powerbank_limit as group_default_limit,
                        ou.name as group_name,
                        CASE 
                            WHEN au.powerbank_limit IS NOT NULL THEN au.powerbank_limit
                            WHEN ou.default_powerbank_limit IS NOT NULL THEN ou.default_powerbank_limit
                            ELSE 0
                        END as effective_limit,
                        CASE 
                            WHEN au.powerbank_limit IS NOT NULL THEN 'individual'
                            WHEN ou.default_powerbank_limit IS NOT NULL THEN 'group'
                            ELSE 'no_group'
                        END as limit_type
                    FROM app_user au
                    LEFT JOIN user_role ur ON au.user_id = ur.user_id
                    LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                    WHERE au.user_id = %s
                    """,
                    (user_id,),
                )

                row = await cur.fetchone()
                if not row:
                    return {
                        "user_id": user_id,
                        "individual_limit": None,
                        "group_default_limit": None,
                        "group_name": None,
                        "effective_limit": 0,
                        "limit_type": "no_user",
                        "active_count": 0,
                    }

                # Получаем телефон пользователя для поиска в orders
                await cur.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                phone_result = await cur.fetchone()
                user_phone = phone_result[0] if phone_result else None
                
                if not user_phone:
                    return {
                        "user_id": user_id,
                        "individual_limit": None,
                        "group_default_limit": None,
                        "group_name": None,
                        "effective_limit": 0,
                        "limit_type": "no_user",
                        "active_count": 0,
                    }

                await cur.execute(
                    """
                    SELECT COUNT(*) as active_count
                    FROM orders o
                    WHERE o.user_phone = %s 
                      AND o.status = 'borrow' 
                      AND o.completed_at IS NULL
                    """,
                    (user_phone,),
                )
                active_row = await cur.fetchone()
                active_count = active_row[0] if active_row else 0

                return {
                    "user_id": row[0],
                    "individual_limit": row[1],
                    "group_default_limit": row[2],
                    "group_name": row[3],
                    "effective_limit": row[4],
                    "limit_type": row[5],
                    "active_count": active_count,
                }
    except Exception as e:
        logger = get_logger('order_utils')
        logger.error(f"Ошибка получения информации о лимите пользователя {user_id}: {e}")

        return {
            "user_id": user_id,
            "individual_limit": None,
            "group_default_limit": None,
            "group_name": None,
            "effective_limit": 0,
            "limit_type": "error",
            "active_count": 0,
            "error": str(e),
        }


async def _get_active_count(conn, user_id: int) -> int:
    async with conn.cursor() as cur:
        # Получаем телефон пользователя
        await cur.execute("""
            SELECT phone_e164 FROM app_user WHERE user_id = %s
        """, (user_id,))
        phone_result = await cur.fetchone()
        if not phone_result:
            return 0
        user_phone = phone_result[0]
        
        await cur.execute(
            """
            SELECT COUNT(*) as active_count
            FROM orders o
            WHERE o.user_phone = %s 
              AND o.status = 'borrow' 
              AND o.completed_at IS NULL
            """,
            (user_phone,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def validate_borrow_request(db_pool, user_id: int, powerbank_id: int, 
                                station_id: int) -> Tuple[bool, str]:
    """
    Комплексная валидация запроса на выдачу powerbank'а
    
    """
    try:
        logger = get_logger('order_utils')
        logger.info(f"Валидация запроса на выдачу: пользователь {user_id}, powerbank {powerbank_id}, станция {station_id}")
        
        # Проверяем лимит повербанков пользователя
        limit_ok, limit_message = await check_user_powerbank_limit(db_pool, user_id)
        if not limit_ok:
            return False, limit_message
        
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

