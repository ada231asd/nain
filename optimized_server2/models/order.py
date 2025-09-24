"""
Модель для работы с заказами
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiomysql


class Order:
    """Модель заказа"""
    
    def __init__(self, order_id: int, station_id: int, user_id: int, 
                 powerbank_id: Optional[int] = None, status: str = 'borrow',
                 timestamp: Optional[datetime] = None):
        self.order_id = order_id
        self.station_id = station_id
        self.user_id = user_id
        self.powerbank_id = powerbank_id
        self.status = status
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует заказ в словарь"""
        return {
            'order_id': self.order_id,
            'station_id': self.station_id,
            'user_id': self.user_id,
            'powerbank_id': self.powerbank_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    async def create_borrow_order(cls, db_pool, station_id: int, user_id: int, 
                                 powerbank_id: int) -> 'Order':
        """Создает заказ на выдачу повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, 'borrow', datetime.now()))
                
                order_id = cursor.lastrowid
                
                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='borrow',
                    timestamp=datetime.now()
                )
    
    @classmethod
    async def create_return_order(cls, db_pool, station_id: int, user_id: int, 
                                powerbank_id: int) -> 'Order':
        """Создает заказ на возврат повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO orders (station_id, user_id, powerbank_id, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (station_id, user_id, powerbank_id, 'return', datetime.now()))
                
                order_id = cursor.lastrowid
                
                return cls(
                    order_id=order_id,
                    station_id=station_id,
                    user_id=user_id,
                    powerbank_id=powerbank_id,
                    status='return',
                    timestamp=datetime.now()
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
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, borrow_time, return_time
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
                        timestamp=result[5],
                        borrow_time=result[6],
                        return_time=result[7]
                    ))
                
                return orders

    @classmethod
    async def get_active_by_user_id(cls, db_pool, user_id: int) -> List['Order']:
        """Получает активные заказы пользователя"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, borrow_time, return_time
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
                        timestamp=result[5],
                        borrow_time=result[6],
                        return_time=result[7]
                    ))
                
                return orders

    @classmethod
    async def get_active_by_powerbank_id(cls, db_pool, powerbank_id: int) -> Optional['Order']:
        """Получает активный заказ по ID повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, user_id, powerbank_id, status, timestamp, borrow_time, return_time
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
                        timestamp=result[5],
                        borrow_time=result[6],
                        return_time=result[7]
                    )
                return None

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