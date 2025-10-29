"""
Модель для работы с заказами
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiomysql
from utils.time_utils import get_moscow_time


class Order:
    """Модель заказа (монолитная структура)"""
    
    def __init__(self, order_id: int, status: str = 'borrow',
                 station_box_id: str = None, user_phone: str = None, user_fio: str = None,
                 powerbank_serial: Optional[str] = None, org_unit_name: Optional[str] = None,
                 timestamp: Optional[datetime] = None, completed_at: Optional[datetime] = None,
                 borrow_time: Optional[datetime] = None, return_time: Optional[datetime] = None):
        self.order_id = order_id
        self.status = status
        self.station_box_id = station_box_id
        self.user_phone = user_phone
        self.user_fio = user_fio
        self.powerbank_serial = powerbank_serial
        self.org_unit_name = org_unit_name
        self.timestamp = timestamp or get_moscow_time()
        self.completed_at = completed_at
        self.borrow_time = borrow_time or (timestamp if status == 'borrow' else None)
        self.return_time = return_time or (completed_at if status == 'return' else None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует заказ в словарь"""
        return {
            'order_id': self.order_id,
            'status': self.status,
            'station_box_id': self.station_box_id,
            'user_phone': self.user_phone,
            'user_fio': self.user_fio,
            'powerbank_serial': self.powerbank_serial,
            'org_unit_name': self.org_unit_name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'borrow_time': self.borrow_time.isoformat() if self.borrow_time else None,
            'return_time': self.return_time.isoformat() if self.return_time else None
        }
    
    @classmethod
    async def create_pending_order(cls, db_pool, user_id: int, powerbank_id: int,
                                 station_id: int) -> 'Order':
        """Создает заказ со статусом pending (ожидание) - монолитная структура"""
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Получаем данные пользователя
                await cursor.execute("""
                    SELECT phone_e164, fio FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_data = await cursor.fetchone()
                
                if not user_data:
                    raise ValueError(f"Пользователь с ID {user_id} не найден")
                
                user_phone = user_data[0]
                user_fio = user_data[1] or f'user_{user_id}'

                # Получаем данные станции
                await cursor.execute("""
                    SELECT box_id, org_unit_id FROM station WHERE station_id = %s
                """, (station_id,))
                station_data = await cursor.fetchone()
                
                if not station_data:
                    raise ValueError(f"Станция с ID {station_id} не найдена")
                
                station_box_id = station_data[0]
                org_unit_id = station_data[1]

                # Получаем данные повербанка
                await cursor.execute("""
                    SELECT serial_number FROM powerbank WHERE id = %s
                """, (powerbank_id,))
                powerbank_data = await cursor.fetchone()
                
                powerbank_serial = powerbank_data[0] if powerbank_data else None

                # Получаем название org_unit если есть
                org_unit_name = None
                if org_unit_id:
                    await cursor.execute("""
                        SELECT name FROM org_unit WHERE org_unit_id = %s
                    """, (org_unit_id,))
                    org_unit_data = await cursor.fetchone()
                    if org_unit_data:
                        org_unit_name = org_unit_data[0]

                # Создаем заказ с монолитными полями
                await cursor.execute("""
                    INSERT INTO orders (
                        station_box_id, user_phone, user_fio,
                        powerbank_serial, org_unit_name,
                        status, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    station_box_id, user_phone, user_fio,
                    powerbank_serial, org_unit_name,
                    'pending'
                ))
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_box_id=station_box_id,
                    user_phone=user_phone,
                    user_fio=user_fio,
                    powerbank_serial=powerbank_serial,
                    org_unit_name=org_unit_name,
                    status='pending',
                    timestamp=current_time,
                    completed_at=None
                )
    
    @classmethod
    async def create(cls, db_pool, station_id: int, user_id: int,
                    powerbank_id: int = None, status: str = 'borrow') -> 'Order':
        """Создает заказ с указанными параметрами"""
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Проверяем существование пользователя
                await cursor.execute("""
                    SELECT user_id FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_exists = await cursor.fetchone()

                if not user_exists:
                    # Создаем системного пользователя для административных операций
                    await cursor.execute("""
                        INSERT INTO app_user (fio, email, phone_e164, status, created_at, powerbank_limit)
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_user
                        ON DUPLICATE KEY UPDATE fio = new_user.fio
                    """, (f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', current_time, 1))

                completed_at_value = current_time if status == 'return' else None

                # Получаем org_unit_id станции
                org_unit_id_value = None
                try:
                    await cursor.execute("""
                        SELECT org_unit_id FROM station WHERE station_id = %s
                    """, (station_id,))
                    row = await cursor.fetchone()
                    if row:
                        org_unit_id_value = row[0]
                except Exception:
                    org_unit_id_value = None

                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, org_unit_id, status, timestamp, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, org_unit_id_value, status, current_time, completed_at_value))
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status=status,
                    timestamp=current_time,
                    completed_at=completed_at_value
                )
    
    @classmethod
    async def create_borrow_order(cls, db_pool, station_id: int, user_id: int,
                                 powerbank_id: int) -> 'Order':
        """Создает заказ на выдачу повербанка (монолитная структура)"""
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Получаем данные пользователя
                await cursor.execute("""
                    SELECT phone_e164, fio FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_data = await cursor.fetchone()
                
                if not user_data:
                    raise ValueError(f"Пользователь с ID {user_id} не найден")
                
                user_phone = user_data[0]
                user_fio = user_data[1] or f'user_{user_id}'

                # Получаем данные станции
                await cursor.execute("""
                    SELECT box_id, org_unit_id FROM station WHERE station_id = %s
                """, (station_id,))
                station_data = await cursor.fetchone()
                
                if not station_data:
                    raise ValueError(f"Станция с ID {station_id} не найдена")
                
                station_box_id = station_data[0]
                org_unit_id = station_data[1]

                # Получаем данные повербанка
                await cursor.execute("""
                    SELECT serial_number FROM powerbank WHERE id = %s
                """, (powerbank_id,))
                powerbank_data = await cursor.fetchone()
                
                powerbank_serial = powerbank_data[0] if powerbank_data else None

                # Получаем название org_unit если есть
                org_unit_name = None
                if org_unit_id:
                    await cursor.execute("""
                        SELECT name FROM org_unit WHERE org_unit_id = %s
                    """, (org_unit_id,))
                    org_unit_data = await cursor.fetchone()
                    if org_unit_data:
                        org_unit_name = org_unit_data[0]

                # Создаем заказ с монолитными полями
                await cursor.execute("""
                    INSERT INTO orders (
                        station_box_id, user_phone, user_fio,
                        powerbank_serial, org_unit_name,
                        status, timestamp, completed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                """, (
                    station_box_id, user_phone, user_fio,
                    powerbank_serial, org_unit_name,
                    'borrow', None
                ))
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_box_id=station_box_id,
                    user_phone=user_phone,
                    user_fio=user_fio,
                    powerbank_serial=powerbank_serial,
                    org_unit_name=org_unit_name,
                    status='borrow',
                    timestamp=current_time,
                    completed_at=None
                )
    
    @classmethod
    async def create_return_order(cls, db_pool, station_id: int, user_id: int,
                                powerbank_id: int) -> 'Order':
        """Создает заказ на возврат повербанка (монолитная структура)"""
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Получаем данные пользователя
                await cursor.execute("""
                    SELECT phone_e164, fio FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_data = await cursor.fetchone()
                
                if not user_data:
                    raise ValueError(f"Пользователь с ID {user_id} не найден")
                
                user_phone = user_data[0]
                user_fio = user_data[1] or f'user_{user_id}'

                # Получаем данные станции
                await cursor.execute("""
                    SELECT box_id, org_unit_id FROM station WHERE station_id = %s
                """, (station_id,))
                station_data = await cursor.fetchone()
                
                if not station_data:
                    raise ValueError(f"Станция с ID {station_id} не найдена")
                
                station_box_id = station_data[0]
                org_unit_id = station_data[1]

                # Получаем данные повербанка
                await cursor.execute("""
                    SELECT serial_number FROM powerbank WHERE id = %s
                """, (powerbank_id,))
                powerbank_data = await cursor.fetchone()
                
                powerbank_serial = powerbank_data[0] if powerbank_data else None

                # Получаем название org_unit если есть
                org_unit_name = None
                if org_unit_id:
                    await cursor.execute("""
                        SELECT name FROM org_unit WHERE org_unit_id = %s
                    """, (org_unit_id,))
                    org_unit_data = await cursor.fetchone()
                    if org_unit_data:
                        org_unit_name = org_unit_data[0]

                # Создаем заказ с монолитными полями
                await cursor.execute("""
                    INSERT INTO orders (
                        station_box_id, user_phone, user_fio,
                        powerbank_serial, org_unit_name,
                        status, timestamp, completed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    station_box_id, user_phone, user_fio,
                    powerbank_serial, org_unit_name,
                    'return'
                ))
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_box_id=station_box_id,
                    user_phone=user_phone,
                    user_fio=user_fio,
                    powerbank_serial=powerbank_serial,
                    org_unit_name=org_unit_name,
                    status='return',
                    timestamp=current_time,
                    completed_at=current_time
                )
    
    @classmethod
    async def get_by_id(cls, db_pool, order_id: int) -> Optional['Order']:
        """Получает заказ по ID (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT * FROM orders WHERE id = %s
                """, (order_id,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result['id'],
                        station_box_id=result.get('station_box_id'),
                        user_phone=result.get('user_phone'),
                        user_fio=result.get('user_fio'),
                        powerbank_serial=result.get('powerbank_serial'),
                        org_unit_name=result.get('org_unit_name'),
                        status=result['status'],
                        timestamp=result.get('timestamp'),
                        completed_at=result.get('completed_at'),
                    )
                return None
    
    @classmethod
    async def get_user_orders(cls, db_pool, user_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы пользователя (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Сначала получаем телефон пользователя по user_id
                await cursor.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_result = await cursor.fetchone()
                
                if not user_result:
                    return []
                
                user_phone = user_result[0]
                
                # Теперь получаем заказы по телефону из монолитной таблицы
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE user_phone = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_phone, limit))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    ))

                return orders
    
    @classmethod
    async def get_active_orders_by_user(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Сначала получаем телефон пользователя по user_id
                await cursor.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_result = await cursor.fetchone()
                
                if not user_result:
                    return []
                
                user_phone = user_result[0]
                
                # Теперь получаем заказы по телефону из монолитной таблицы
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE user_phone = %s AND status IN ('borrow', 'return_damage')
                    ORDER BY timestamp DESC
                """, (user_phone,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    ))

                return orders
    
    @classmethod
    async def get_station_orders(cls, db_pool, station_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы станции (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Сначала получаем box_id станции по station_id
                await cursor.execute("""
                    SELECT box_id FROM station WHERE station_id = %s
                """, (station_id,))
                station_result = await cursor.fetchone()
                
                if not station_result:
                    return []
                
                station_box_id = station_result[0]
                
                # Теперь получаем заказы по box_id из монолитной таблицы
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE station_box_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (station_box_id, limit))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    ))

                return orders

    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает все заказы пользователя (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Сначала получаем телефон пользователя по user_id
                await cursor.execute("""
                    SELECT phone_e164 FROM app_user WHERE user_id = %s
                """, (user_id,))
                user_result = await cursor.fetchone()
                
                if not user_result:
                    return []
                
                user_phone = user_result[0]
                
                # Теперь получаем все заказы по телефону из монолитной таблицы
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE user_phone = %s
                    ORDER BY timestamp DESC
                """, (user_phone,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    ))

                return orders

    @classmethod
    async def get_active_by_user_phone(cls, db_pool, user_phone: str) -> List['Order']:
        """Получает активные заказы пользователя по телефону"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT * FROM orders
                    WHERE user_phone = %s AND status = 'borrow'
                    ORDER BY timestamp DESC
                """, (user_phone,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result['id'],
                        station_box_id=result.get('station_box_id'),
                        user_phone=result.get('user_phone'),
                        user_fio=result.get('user_fio'),
                        powerbank_serial=result.get('powerbank_serial'),
                        org_unit_name=result.get('org_unit_name'),
                        status=result['status'],
                        timestamp=result.get('timestamp'),
                        completed_at=result.get('completed_at'),
                    ))

                return orders

    @classmethod
    async def get_active_by_powerbank_serial(cls, db_pool, powerbank_serial: str) -> Optional['Order']:
        """Получает активный заказ по серийному номеру повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT * FROM orders
                    WHERE powerbank_serial = %s AND status = 'borrow'
                    LIMIT 1
                """, (powerbank_serial,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result['id'],
                        station_box_id=result.get('station_box_id'),
                        user_phone=result.get('user_phone'),
                        user_fio=result.get('user_fio'),
                        powerbank_serial=result.get('powerbank_serial'),
                        org_unit_name=result.get('org_unit_name'),
                        status=result['status'],
                        timestamp=result.get('timestamp'),
                        completed_at=result.get('completed_at'),
                    )
                return None

    @classmethod
    async def get_active_by_station_box_id(cls, db_pool, station_box_id: str) -> List['Order']:
        """Получает активные заказы для станции по box_id"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT * FROM orders
                    WHERE station_box_id = %s AND status = 'borrow'
                    ORDER BY timestamp DESC
                """, (station_box_id,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result['id'],
                        station_box_id=result.get('station_box_id'),
                        user_phone=result.get('user_phone'),
                        user_fio=result.get('user_fio'),
                        powerbank_serial=result.get('powerbank_serial'),
                        org_unit_name=result.get('org_unit_name'),
                        status=result['status'],
                        timestamp=result.get('timestamp'),
                        completed_at=result.get('completed_at'),
                    ))

                return orders

    @classmethod
    async def get_count_by_user_phone(cls, db_pool, user_phone: str) -> int:
        """Получает количество заказов пользователя по телефону"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT COUNT(*) FROM orders WHERE user_phone = %s
                """, (user_phone,))
                
                result = await cursor.fetchone()
                return result[0] if result else 0

    
    async def update_status(self, db_pool, new_status: str) -> bool:
        """Обновляет статус заказа. Для 'return' устанавливает completed_at."""
        from utils.centralized_logger import get_logger
        logger = get_logger('order_model')
        
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if new_status == 'return':
                    logger.info(f"Обновление заказа {self.order_id}: статус -> 'return', completed_at -> {current_time}")
                    await cursor.execute(
                        "UPDATE orders SET status = %s, completed_at = %s WHERE id = %s",
                        (new_status, current_time, self.order_id)
                    )
                    self.completed_at = current_time
                    logger.info(f"Заказ {self.order_id} обновлен в БД: status='{new_status}', completed_at={current_time}")
                else:  # Для 'borrow' и других статусов
                    logger.info(f"Обновление заказа {self.order_id}: статус -> '{new_status}', completed_at -> NULL")
                    await cursor.execute(
                        "UPDATE orders SET status = %s, completed_at = NULL WHERE id = %s",
                        (new_status, self.order_id)
                    )
                    self.completed_at = None
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД
                self.status = new_status
                logger.info(f"Заказ {self.order_id}: транзакция завершена, новый статус сохранен в БД")
                return True
    
    @classmethod
    async def get_active_borrow_order(cls, db_pool, powerbank_serial: str) -> Optional['Order']:
        """Получает активный заказ на выдачу для повербанка (по serial_number)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE powerbank_serial = %s AND status = 'borrow' AND completed_at IS NULL
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (powerbank_serial,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    )
                return None
    
    @classmethod
    async def confirm_borrow(cls, db_pool, order_id: int) -> bool:
        """Подтверждает заказ на выдачу ('borrow')"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE orders SET status = 'borrow' 
                    WHERE id = %s
                """, (order_id,))
                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД
                
                return cursor.rowcount > 0
    
    
    @classmethod
    async def update_order_status(cls, db_pool, order_id: int, new_status: str) -> bool:
        """Обновляет статус заказа"""
        allowed_statuses = ['borrow', 'return']
        if new_status not in allowed_statuses:
            print(f"Недопустимый статус заказа: {new_status}. Допустимые: {allowed_statuses}")
            return False

        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if new_status == 'return':
                    await cursor.execute("""
                        UPDATE orders SET status = %s, completed_at = %s WHERE id = %s
                    """, (new_status, current_time, order_id))
                else:  # Для 'borrow' и других статусов
                    await cursor.execute("""
                        UPDATE orders SET status = %s, completed_at = NULL WHERE id = %s
                    """, (new_status, order_id))

                await conn.commit()  # КРИТИЧНО: сохраняем изменения в БД
                return cursor.rowcount > 0
    
    @classmethod
    async def get_all_active(cls, db_pool) -> List['Order']:
        """Получает все активные заказы (монолитная структура)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_box_id, user_phone, user_fio, powerbank_serial, 
                           org_unit_name, status, timestamp, completed_at
                    FROM orders
                    WHERE status IN ('borrow', 'pending', 'return_damage')
                    ORDER BY timestamp DESC
                """)

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_box_id=result[1],
                        user_phone=result[2],
                        user_fio=result[3],
                        powerbank_serial=result[4],
                        org_unit_name=result[5],
                        status=result[6],
                        timestamp=result[7],
                        completed_at=result[8],
                    ))

                return orders
    
    @classmethod
    async def get_extended_by_id(cls, db_pool, order_id: int) -> Optional[Dict[str, Any]]:
        """Получить расширенные данные заказа по ID из представления v_orders_extended"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM v_orders_extended WHERE id = %s
                """, (order_id,))
                
                result = await cur.fetchone()
                return result
    
    @classmethod
    async def get_extended_by_user_id(cls, db_pool, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить расширенные данные заказов пользователя из представления v_orders_extended"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM v_orders_extended 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))
                
                results = await cur.fetchall()
                return results
    
    @classmethod
    async def get_extended_by_station_id(cls, db_pool, station_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить расширенные данные заказов станции из представления v_orders_extended"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM v_orders_extended 
                    WHERE station_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s OFFSET %s
                """, (station_id, limit, offset))
                
                results = await cur.fetchall()
                return results
    
    @classmethod
    async def get_extended_by_status(cls, db_pool, status: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить расширенные данные заказов по статусу из представления v_orders_extended"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM v_orders_extended 
                    WHERE status = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s OFFSET %s
                """, (status, limit, offset))
                
                results = await cur.fetchall()
                return results
    
    @classmethod
    async def search_extended_orders(cls, db_pool, filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Поиск заказов с расширенными данными по фильтрам"""
        where_conditions = []
        params = []
        
        if 'status' in filters and filters['status']:
            where_conditions.append("status = %s")
            params.append(filters['status'])
        
        if 'user_id' in filters and filters['user_id']:
            where_conditions.append("user_id = %s")
            params.append(int(filters['user_id']))
        
        if 'station_id' in filters and filters['station_id']:
            where_conditions.append("station_id = %s")
            params.append(int(filters['station_id']))
        
        if 'org_unit_id' in filters and filters['org_unit_id']:
            where_conditions.append("org_unit_id = %s")
            params.append(int(filters['org_unit_id']))
        
        if 'date_from' in filters and filters['date_from']:
            where_conditions.append("timestamp >= %s")
            params.append(filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            where_conditions.append("timestamp <= %s")
            params.append(filters['date_to'])
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Получаем общее количество
                count_query = f"SELECT COUNT(*) as total FROM v_orders_extended {where_clause}"
                await cur.execute(count_query, params)
                total = (await cur.fetchone())['total']
                
                # Получаем данные
                query = f"""
                    SELECT * FROM v_orders_extended
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """
                await cur.execute(query, params + [limit, offset])
                orders = await cur.fetchall()
                
                return {
                    'orders': orders,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }