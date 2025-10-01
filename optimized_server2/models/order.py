"""
Модель для работы с заказами
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiomysql
from utils.packet_utils import get_moscow_time


class Order:
    """Модель заказа"""
    
    def __init__(self, order_id: int, station_id: int, user_id: int, 
                 powerbank_id: Optional[int] = None, status: str = 'borrow',
                 timestamp: Optional[datetime] = None, borrow_time: Optional[datetime] = None,
                 return_time: Optional[datetime] = None, order_type: str = 'borrow', notes: str = None):
        self.order_id = order_id
        self.station_id = station_id
        self.user_id = user_id
        self.powerbank_id = powerbank_id
        self.status = status
        self.timestamp = timestamp or get_moscow_time()
        self.borrow_time = borrow_time
        self.return_time = return_time
        self.order_type = order_type
        self.notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует заказ в словарь"""
        return {
            'order_id': self.order_id,
            'station_id': self.station_id,
            'user_id': self.user_id,
            'powerbank_id': self.powerbank_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'borrow_time': self.borrow_time.isoformat() if self.borrow_time else None,
            'return_time': self.return_time.isoformat() if self.return_time else None
        }
    
    @classmethod
    async def create(cls, db_pool, station_id: int, user_id: int, 
                    powerbank_id: int = None, order_type: str = 'borrow', 
                    status: str = 'borrow', notes: str = None) -> 'Order':
        """Создает заказ с указанными параметрами"""
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
                        INSERT INTO app_user (user_id, username, email, phone, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                        ON DUPLICATE KEY UPDATE username = new_values.username
                    """, (user_id, f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', get_moscow_time()))
                
                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, order_type, status, notes, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, order_type, status, notes, get_moscow_time()))
                
                order_id = cursor.lastrowid
                
                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    order_type=order_type,
                    status=status,
                    notes=notes,
                    timestamp=get_moscow_time()
                )
    
    @classmethod
    async def create_borrow_order(cls, db_pool, station_id: int, user_id: int, 
                                 powerbank_id: int) -> 'Order':
        """Создает заказ на выдачу повербанка"""
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
                        INSERT INTO app_user (user_id, username, email, phone, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                        ON DUPLICATE KEY UPDATE username = new_values.username
                    """, (user_id, f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', get_moscow_time()))
                
                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, 'borrow', get_moscow_time()))
                
                order_id = cursor.lastrowid
                
                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='borrow',
                    timestamp=get_moscow_time()
                )
    
    @classmethod
    async def create_return_order(cls, db_pool, station_id: int, user_id: int, 
                                powerbank_id: int) -> 'Order':
        """Создает заказ на возврат повербанка"""
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
                        INSERT INTO app_user (user_id, username, email, phone, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s) AS new_values
                        ON DUPLICATE KEY UPDATE username = new_values.username
                    """, (user_id, f'system_user_{user_id}', f'system_{user_id}@local', '0000000000', 'active', get_moscow_time()))
                
                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, 'return', get_moscow_time()))
                
                order_id = cursor.lastrowid
                
                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='return',
                    timestamp=get_moscow_time()
                )
    
    @classmethod
    async def get_by_id(cls, db_pool, order_id: int) -> Optional['Order']:
        """Получает заказ по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
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
                        timestamp=result[5]
                    )
                return None
    
    @classmethod
    async def get_user_orders(cls, db_pool, user_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    ))
                
                return orders
    
    @classmethod
    async def get_active_orders_by_user(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    ))
                
                return orders
    
    @classmethod
    async def get_station_orders(cls, db_pool, station_id: int, limit: int = 10) -> List['Order']:
        """Получает заказы станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    ))
                
                return orders

    @classmethod
    async def get_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает все заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    ))
                
                return orders

    @classmethod
    async def get_active_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    ))
                
                return orders

    @classmethod
    async def get_active_by_powerbank_id(cls, db_pool, powerbank_id: int) -> Optional['Order']:
        """Получает активный заказ по ID повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
                    WHERE powerbank_id = %s AND status = 'active'
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
                        timestamp=result[5]
                    )
                return None

    @classmethod
    async def get_active_by_station_id(cls, db_pool, station_id: int) -> List['Order']:
        """Получает активные заказы для станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
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

    @classmethod
    async def cancel(cls, db_pool, order_id: int) -> bool:
        """Отменяет заказ"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE orders SET status = 'cancelled' WHERE id = %s
                """, (order_id,))
                
                return cursor.rowcount > 0
    
    async def update_status(self, db_pool, new_status: str) -> bool:
        """Обновляет статус заказа"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s",
                    (new_status, self.order_id)
                )
                self.status = new_status
                return True
    
    @classmethod
    async def get_active_borrow_order(cls, db_pool, powerbank_id: int) -> Optional['Order']:
        """Получает активный заказ на выдачу для повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp
                    FROM orders 
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
                        timestamp=result[5]
                    )
                return None
    
    @classmethod
    async def complete_order(cls, db_pool, order_id: int) -> bool:
        """Завершает заказ (меняет статус на 'completed')"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE orders SET status = 'completed' WHERE id = %s
                """, (order_id,))
                
                return cursor.rowcount > 0
    
    @classmethod
    async def update_order_status(cls, db_pool, order_id: int, new_status: str) -> bool:
        """Обновляет статус заказа"""
        # Проверяем, что статус соответствует допустимым значениям
        allowed_statuses = ['borrow', 'return', 'force_eject']
        if new_status not in allowed_statuses:
            print(f"Недопустимый статус заказа: {new_status}. Допустимые: {allowed_statuses}")
            return False
            
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE orders SET status = %s WHERE id = %s
                """, (new_status, order_id))
                
                return cursor.rowcount > 0