"""
HTTP endpoints для возврата повербанков с ошибкой
"""
from aiohttp import web
from typing import Dict, Any
import json

from handlers.return_powerbank import ReturnPowerbankHandler


class ReturnEndpoints:
    """HTTP endpoints для возврата повербанков с ошибкой"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.return_handler = ReturnPowerbankHandler(db_pool, connection_manager)
    
    def setup_routes(self, app):
        """Настраивает маршруты для возврата повербанков с ошибкой"""
        
        # Запрос на возврат с ошибкой
        app.router.add_post('/api/return/error', self.request_error_return)
        
        # Получить ожидающие возврат с ошибкой
        app.router.add_get('/api/return/error/pending', self.get_pending_error_returns)
        
        # Отменить ожидание возврата с ошибкой
        app.router.add_delete('/api/return/error/pending/{user_id}', self.cancel_error_return)
        
        # Получить типы ошибок
        app.router.add_get('/api/return/error/types', self.get_error_types)
        
        # Очистить просроченные запросы (админ)
        app.router.add_post('/api/return/error/cleanup', self.cleanup_expired_requests)
    
    async def request_error_return(self, request):
        """POST /api/return/error - Запрос на возврат повербанка с ошибкой"""
        try:
            data = await request.json()
            
            # Валидация обязательных полей
            required_fields = ['user_id', 'station_id', 'error_type']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            user_id = int(data['user_id'])
            station_id = int(data['station_id'])
            error_type = int(data['error_type'])
            
            # Обрабатываем запрос
            result = await self.return_handler.handle_error_return_request(user_id, station_id, error_type)
            
            if result.get('success'):
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка валидации данных: {str(e)}"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка обработки запроса: {str(e)}"
            }, status=500)
    
    async def get_pending_error_returns(self, request):
        """GET /api/return/error/pending - Получить ожидающие возврат с ошибкой"""
        try:
            # Получаем user_id из query параметров (опционально)
            user_id = request.query.get('user_id')
            if user_id:
                user_id = int(user_id)
            
            result = await self.return_handler.get_pending_error_returns()
            
            if result.get('success'):
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка валидации параметров: {str(e)}"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка получения данных: {str(e)}"
            }, status=500)
    
    async def cancel_error_return(self, request):
        """DELETE /api/return/error/pending/{user_id} - Отменить ожидание возврата с ошибкой"""
        try:
            user_id = int(request.match_info['user_id'])
            
            result = await self.return_handler.cancel_error_return(user_id)
            
            if result.get('success'):
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка валидации параметров: {str(e)}"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка отмены: {str(e)}"
            }, status=500)
    
    async def get_error_types(self, request):
        """GET /api/return/error/types - Получить типы ошибок"""
        try:
            result = await self.return_handler.get_error_types()
            
            if result.get('success'):
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка получения типов ошибок: {str(e)}"
            }, status=500)
    
    async def cleanup_expired_requests(self, request):
        """POST /api/return/error/cleanup - Очистить просроченные запросы"""
        try:
            data = await request.json() if request.content_length else {}
            max_age_minutes = data.get('max_age_minutes', 30)
            
            result = await self.return_handler.cleanup_expired_requests(max_age_minutes)
            
            if result.get('success'):
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": f"Ошибка очистки: {str(e)}"
            }, status=500)
