"""
HTTP endpoints для выдачи повербанков
"""
from aiohttp import web
from typing import Dict, Any
import json

from api.borrow_powerbank_api import BorrowPowerbankAPI


class BorrowEndpoints:
    """HTTP endpoints для выдачи повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.borrow_api = BorrowPowerbankAPI(db_pool, connection_manager)
    
    def setup_routes(self, app):
        """Настраивает маршруты для выдачи повербанков"""
        
        # Получить список доступных повербанков в станции
        async def get_available_powerbanks(request):
            """Получить список доступных повербанков в станции"""
            try:
                station_id = int(request.match_info['station_id'])
                
                # Извлекаем user_id из JWT токена, если он есть
                user_id = None
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    try:
                        from handlers.auth_handler import AuthHandler
                        auth_handler = AuthHandler(self.db_pool)
                        token = auth_header.split(' ')[1]
                        payload = auth_handler.verify_jwt_token(token)
                        if payload:
                            from models.user import User
                            user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
                            if user:
                                user_id = user.user_id
                    except Exception:
                        # Игнорируем ошибки авторизации для этого эндпоинта
                        pass
                
                result = await self.borrow_api.get_available_powerbanks(station_id, user_id)
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Получить статус слота
        async def get_slot_status(request):
            """Получить статус слота"""
            try:
                station_id = int(request.match_info['station_id'])
                slot_number = int(request.match_info['slot_number'])
                result = await self.borrow_api.get_borrow_status(station_id, slot_number)
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Запросить выдачу повербанка
        async def request_borrow(request):
            """Запросить выдачу повербанка"""
            try:
                station_id = int(request.match_info['station_id'])
                data = await request.json()
                
                if not data:
                    return web.json_response(
                        {"error": "Отсутствуют данные запроса", "success": False}, 
                        status=400
                    )
                
                slot_number = data.get('slot_number')
                user_id = data.get('user_id')
                
                if slot_number is None or user_id is None:
                    return web.json_response({
                        "error": "Отсутствуют обязательные поля: slot_number, user_id", 
                        "success": False
                    }, status=400)
                
                result = await self.borrow_api.request_borrow(station_id, slot_number, user_id)
                
                if result.get('success'):
                    return web.json_response(result)
                else:
                    # Добавляем детальное логирование ошибки
                    from utils.centralized_logger import get_logger
                    logger = get_logger('borrow_endpoints')
                    logger.error(f"Ошибка выдачи повербанка: станция {station_id}, слот {slot_number}, пользователь {user_id}, ошибка: {result.get('error', 'Неизвестная ошибка')}")
                    return web.json_response(result, status=400)
                    
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Получить информацию о станции
        async def get_station_info(request):
            """Получить информацию о станции"""
            try:
                station_id = int(request.match_info['station_id'])
                result = await self.borrow_api.get_station_info(station_id)
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Выбрать оптимальный повербанк
        async def select_optimal_powerbank(request):
            """Выбрать оптимальный повербанк для выдачи"""
            try:
                station_id = int(request.match_info['station_id'])
                result = await self.borrow_api.select_optimal_powerbank(station_id)
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Запросить выдачу оптимального повербанка
        async def request_optimal_borrow(request):
            """Запросить выдачу оптимального повербанка (автоматический выбор)"""
            try:
                station_id = int(request.match_info['station_id'])
                data = await request.json()
                
                if not data:
                    return web.json_response(
                        {"error": "Отсутствуют данные запроса", "success": False}, 
                        status=400
                    )
                
                user_id = data.get('user_id')
                
                if user_id is None:
                    return web.json_response({
                        "error": "Отсутствует обязательное поле: user_id", 
                        "success": False
                    }, status=400)
                
                result = await self.borrow_api.request_optimal_borrow(station_id, user_id)
                
                if result.get('success'):
                    return web.json_response(result)
                else:
                    return web.json_response(result, status=400)
                    
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Запрос на выдачу повербанка по его ID 
        async def request_borrow_by_powerbank_id(request):
            """Запросить выдачу повербанка по его ID"""
            try:
                powerbank_id = int(request.match_info['powerbank_id'])
                data = await request.json()
                
                if not data:
                    return web.json_response(
                        {"error": "Отсутствуют данные запроса", "success": False}, 
                        status=400
                    )
                
                user_id = data.get('user_id')
                
                if user_id is None:
                    return web.json_response({
                        "error": "Отсутствует обязательное поле: user_id", 
                        "success": False
                    }, status=400)
                
                result = await self.borrow_api.request_borrow_by_powerbank_id(powerbank_id, user_id)
                
                if result.get('success'):
                    return web.json_response(result)
                else:
                    return web.json_response(result, status=400)
                    
            except Exception as e:
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Регистрируем маршруты
        app.router.add_get('/api/borrow/stations/{station_id}/powerbanks', get_available_powerbanks)
        app.router.add_get('/api/borrow/stations/{station_id}/slots/{slot_number}/status', get_slot_status)
        app.router.add_post('/api/borrow/stations/{station_id}/request', request_borrow)
        app.router.add_get('/api/borrow/stations/{station_id}/info', get_station_info)
        app.router.add_get('/api/borrow/stations/{station_id}/select-optimal', select_optimal_powerbank)
        app.router.add_post('/api/borrow/stations/{station_id}/request-optimal', request_optimal_borrow)
        app.router.add_post('/api/borrow/powerbanks/{powerbank_id}/request', request_borrow_by_powerbank_id)
