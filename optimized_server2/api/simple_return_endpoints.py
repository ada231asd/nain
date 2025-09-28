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
        app.router.add_post('/return-powerbank', return_powerbank)
        app.router.add_get('/api/return/stations/{station_id}/active-orders', get_active_orders)
