"""
Модель для работы с заказами
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiomysql
from utils.time_utils import get_moscow_time


class Order:
    """Модель заказа"""
    
    def __init__(self, order_id: int, station_id: int, user_id: int,
                 powerbank_id: Optional[int] = None, status: str = 'borrow',
                 timestamp: Optional[datetime] = None, completed_at: Optional[datetime] = None,
                 borrow_time: Optional[datetime] = None, return_time: Optional[datetime] = None):
        self.order_id = order_id
        self.station_id = station_id
        self.user_id = user_id
        self.powerbank_id = powerbank_id
        self.status = status
        self.timestamp = timestamp or get_moscow_time()
        self.completed_at = completed_at
        self.borrow_time = borrow_time or (timestamp if status == 'borrow' else None)
        self.return_time = return_time or (completed_at if status == 'return' else None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует заказ в словарь"""
        return {
            'order_id': self.order_id,
            'station_id': self.station_id,
            'user_id': self.user_id,
            'powerbank_id': self.powerbank_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'borrow_time': self.borrow_time.isoformat() if self.borrow_time else None,
            'return_time': self.return_time.isoformat() if self.return_time else None
        }
    
    @classmethod
    async def create_pending_order(cls, db_pool, user_id: int, powerbank_id: int,
                                 station_id: int) -> 'Order':
        """Создает заказ со статусом pending (ожидание)"""

        return await cls.create(db_pool, station_id, user_id, powerbank_id,
                              status='pending')
    
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
        """Создает заказ на выдачу повербанка"""
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
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                        ON DUPLICATE KEY UPDATE fio = new_values.fio
                    """, (f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', current_time, 1))

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
                """, (station_id, user_id, powerbank_id, org_unit_id_value, 'borrow', current_time, None))

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='borrow',
                    timestamp=current_time,
                    completed_at=None
                )
    
    @classmethod
    async def create_return_order(cls, db_pool, station_id: int, user_id: int,
                                powerbank_id: int) -> 'Order':
        """Создает заказ на возврат повербанка"""
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
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                        ON DUPLICATE KEY UPDATE fio = new_values.fio
                    """, (f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', current_time, 1))

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
                """, (station_id, user_id, powerbank_id, org_unit_id_value, 'return', current_time, current_time))

                order_id = cursor.lastrowid

                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='return',
                    timestamp=current_time,
                    completed_at=current_time
                )
    
    @classmethod
    async def get_by_id(cls, db_pool, order_id: int) -> Optional['Order']:
        """Получает заказ по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at
                    FROM orders WHERE id = %s
                """, (order_id,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    )
                return None
    
    @classmethod
    async def get_user_orders(cls, db_pool, user_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_id, limit))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders
    
    @classmethod
    async def get_active_orders_by_user(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE user_id = %s AND status IN ('borrow', 'return_damage')
                    ORDER BY timestamp DESC
                """, (user_id,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders
    
    @classmethod
    async def get_station_orders(cls, db_pool, station_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE station_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (station_id, limit))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders

    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает все заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                """, (user_id,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders

    @classmethod
    async def get_active_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE user_id = %s AND status = 'active'
                    ORDER BY timestamp DESC
                """, (user_id,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders

    @classmethod
    async def get_active_by_powerbank_id(cls, db_pool, powerbank_id: int) -> Optional['Order']:
        """Получает активный заказ по ID повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE powerbank_id = %s AND status = 'borrow'
                    LIMIT 1
                """, (powerbank_id,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    )
                return None

    @classmethod
    async def get_active_by_station_id(cls, db_pool, station_id: int) -> List['Order']:
        """Получает активные заказы для станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE station_id = %s AND status = 'active'
                    ORDER BY timestamp DESC
                """, (station_id,))

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
                    ))

                return orders

    @classmethod
    async def get_count_by_user_id(cls, db_pool, user_id: int) -> int:
        """Получает количество заказов пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT COUNT(*) FROM orders WHERE user_id = %s
                """, (user_id,))
                
                result = await cursor.fetchone()
                return result[0] if result else 0

    
    async def update_status(self, db_pool, new_status: str) -> bool:
        """Обновляет статус заказа. Для 'return' устанавливает completed_at."""
        current_time = get_moscow_time()
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if new_status == 'return':
                    await cursor.execute(
                        "UPDATE orders SET status = %s, completed_at = %s WHERE id = %s",
                        (new_status, current_time, self.order_id)
                    )
                    self.completed_at = current_time
                else:  # Для 'borrow' и других статусов
                    await cursor.execute(
                        "UPDATE orders SET status = %s, completed_at = NULL WHERE id = %s",
                        (new_status, self.order_id)
                    )
                    self.completed_at = None
                self.status = new_status
                return True
    
    @classmethod
    async def get_active_borrow_order(cls, db_pool, powerbank_id: int) -> Optional['Order']:
        """Получает активный заказ на выдачу для повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at                    FROM orders
                    WHERE powerbank_id = %s AND status = 'borrow'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (powerbank_id,))

                result = await cursor.fetchone()

                if result:
                    return cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
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

                return cursor.rowcount > 0
    
    @classmethod
    async def get_all_active(cls, db_pool) -> List['Order']:
        """Получает все активные заказы"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, completed_at
                    FROM orders
                    WHERE status IN ('borrow', 'pending', 'return_damage')
                    ORDER BY timestamp DESC
                """)

                results = await cursor.fetchall()

                orders = []
                for result in results:
                    orders.append(cls(
                        order_id=result[0],
                        station_id=result[1],
                        user_id=result[2],
                        powerbank_id=result[3],
                        status=result[4],
                        timestamp=result[5],
                        completed_at=result[6],
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