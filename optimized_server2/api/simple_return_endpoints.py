"""
HTTP endpoints для упрощенного возврата повербанков
"""
from aiohttp import web
from typing import Dict, Any
import json

from api.simple_return_api import SimpleReturnAPI


class SimpleReturnEndpoints:
    """HTTP endpoints для упрощенного возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.return_api = SimpleReturnAPI(db_pool, connection_manager)
    
    def setup_routes(self, app):
        """Настраивает маршруты для возврата повербанков"""
        
        # Вернуть повербанк
        async def return_powerbank(request):
            """Вернуть повербанк"""
            try:
                data = await request.json()
                
                print(f" SimpleReturnEndpoints: Получен запрос на возврат - {data}")
                
                if not data:
                    return web.json_response(
                        {"error": "Отсутствуют данные запроса", "success": False}, 
                        status=400
                    )
                
                # Извлекаем данные из запроса
                station_id = data.get('station_id')
                user_id = data.get('user_id')
                powerbank_id = data.get('powerbank_id')
                
                if not all([station_id, user_id, powerbank_id]):
                    return web.json_response(
                        {"error": "Отсутствуют обязательные поля: station_id, user_id, powerbank_id", "success": False}, 
                        status=400
                    )
                
                # Выполняем возврат повербанка
                result = await self.return_api.return_powerbank(
                    station_id=int(station_id),
                    user_id=int(user_id),
                    powerbank_id=int(powerbank_id)
                )
                
                if result.get('success'):
                    return web.json_response(result)
                else:
                    return web.json_response(result, status=400)
                    
            except Exception as e:
                print(f" SimpleReturnEndpoints: Ошибка сервера: {e}")
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Получить активные заказы для станции
        async def get_active_orders(request):
            """Получить активные заказы для станции"""
            try:
                station_id = int(request.match_info['station_id'])
                
                print(f" SimpleReturnEndpoints: Получение активных заказов - station_id={station_id}")
                
                # Получаем активные заказы для станции
                from models.order import Order
                active_orders = await Order.get_active_by_station_id(self.db_pool, station_id)
                
                orders_data = []
                for order in active_orders:
                    orders_data.append({
                        'order_id': order.order_id,
                        'station_id': order.station_id,
                        'user_id': order.user_id,
                        'powerbank_id': order.powerbank_id,
                        'status': order.status,
                        'timestamp': order.timestamp.isoformat() if order.timestamp else None
                    })
                
                return web.json_response({
                    "success": True,
                    "orders": orders_data,
                    "count": len(orders_data)
                })
                
            except Exception as e:
                print(f" SimpleReturnEndpoints: Ошибка получения активных заказов: {e}")
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Регистрируем маршруты
        app.router.add_post('/api/return-powerbank', return_powerbank)
        app.router.add_get('/api/return/stations/{station_id}/active-orders', get_active_orders)

        # Ожидание подтверждения возврата (до 10 сек)
        async def wait_return_confirmation(request):
            try:
                data = await request.json()
                if not data:
                    return web.json_response({"success": False, "error": "Отсутствуют данные запроса"}, status=400)

                station_id = data.get('station_id')
                user_id = data.get('user_id')
                powerbank_id = data.get('powerbank_id')
                timeout_seconds = int(data.get('timeout_seconds') or 10)
                message = data.get('message')

                if not station_id or not user_id:
                    return web.json_response({
                        "success": False,
                        "error": "Отсутствуют обязательные поля: station_id, user_id"
                    }, status=400)

                import asyncio
                from utils.time_utils import get_moscow_time

                deadline = get_moscow_time().timestamp() + max(1, min(60, timeout_seconds))

                async def _fetch_active_user_powerbank_ids(conn):
                    async with conn.cursor() as cur:
                        if powerbank_id:
                            await cur.execute(
                                """
                                SELECT powerbank_id
                                FROM orders
                                WHERE user_id=%s AND status='borrow' AND completed_at IS NULL AND powerbank_id=%s
                                """,
                                (int(user_id), int(powerbank_id))
                            )
                        else:
                            await cur.execute(
                                """
                                SELECT powerbank_id
                                FROM orders
                                WHERE user_id=%s AND status='borrow' AND completed_at IS NULL
                                """,
                                (int(user_id),)
                            )
                        rows = await cur.fetchall()
                        return [r[0] for r in rows if r and r[0] is not None]

                async def _check_returned_in_station(conn, candidate_powerbank_ids):
                    if not candidate_powerbank_ids:
                        return None
                    placeholders = ','.join(['%s'] * len(candidate_powerbank_ids))
                    query = f"""
                        SELECT sp.powerbank_id, sp.slot_number
                        FROM station_powerbank sp
                        WHERE sp.station_id=%s AND sp.powerbank_id IN ({placeholders})
                        LIMIT 1
                    """
                    params = [int(station_id)] + [int(pid) for pid in candidate_powerbank_ids]
                    async with self.db_pool.acquire() as conn2:
                        async with conn2.cursor() as cur:
                            await cur.execute(query, params)
                            row = await cur.fetchone()
                            if row:
                                return {"powerbank_id": row[0], "slot_number": row[1]}
                            return None

                async with self.db_pool.acquire() as conn:
                    while get_moscow_time().timestamp() < deadline:
                        candidate_ids = await _fetch_active_user_powerbank_ids(conn)

                        # Если активных заказов нет — возможно, возврат уже оформлен
                        if not candidate_ids:
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    """
                                    SELECT id, powerbank_id
                                    FROM orders
                                    WHERE user_id=%s AND station_id=%s AND status='return'
                                    ORDER BY timestamp DESC
                                    LIMIT 1
                                    """,
                                    (int(user_id), int(station_id))
                                )
                                row = await cur.fetchone()
                                if row:
                                    return web.json_response({
                                        "success": True,
                                        "station_id": int(station_id),
                                        "user_id": int(user_id),
                                        "confirmed": True,
                                        "powerbank_id": int(row[1]) if row[1] is not None else None,
                                        "timeout": False,
                                        "message": message
                                    })

                        appeared = await _check_returned_in_station(conn, candidate_ids)
                        if appeared:
                            return web.json_response({
                                "success": True,
                                "station_id": int(station_id),
                                "user_id": int(user_id),
                                "confirmed": True,
                                "powerbank_id": int(appeared["powerbank_id"]),
                                "slot_number": int(appeared["slot_number"]) if appeared["slot_number"] is not None else None,
                                "timeout": False,
                                "message": message
                            })

                        await asyncio.sleep(1)

                return web.json_response({
                    "success": False,
                    "station_id": int(station_id),
                    "user_id": int(user_id),
                    "confirmed": False,
                    "timeout": True,
                    "message": message,
                    "error": "Не удалось подтвердить возврат в отведенное время"
                }, status=408)
            except Exception as e:
                return web.json_response({
                    "success": False,
                    "error": f"Ошибка сервера: {str(e)}"
                }, status=500)

        app.router.add_post('/api/return/wait-confirmation', wait_return_confirmation)