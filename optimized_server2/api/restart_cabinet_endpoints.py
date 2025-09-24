"""
HTTP endpoints для команды Remote Restart Cabinet (0x67)
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any

from api.restart_cabinet_api import RestartCabinetAPI


class RestartCabinetEndpoints:
    """HTTP endpoints для команды перезагрузки станции"""
    
    def __init__(self, db_pool, connection_manager):
        self.restart_api = RestartCabinetAPI(db_pool, connection_manager)
    
    async def restart_station(self, request: Request) -> Response:
        """POST /api/restart-station - отправка команды перезагрузки на станцию"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['station_id', 'admin_user_id']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            station_id = data['station_id']
            admin_user_id = data['admin_user_id']
            
            # Валидация типов данных
            try:
                station_id = int(station_id)
                admin_user_id = int(admin_user_id)
            except (ValueError, TypeError):
                return web.json_response({
                    "success": False,
                    "error": "station_id и admin_user_id должны быть числами"
                }, status=400)
            
            # Отправляем команду перезагрузки
            result = await self.restart_api.restart_station(station_id, admin_user_id)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_station_status(self, request: Request) -> Response:
        """GET /api/station-status/{station_id} - получение статуса станции"""
        try:
            station_id = int(request.match_info['station_id'])
            
            result = await self.restart_api.get_station_status(station_id)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=404)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для команды перезагрузки"""
        app.router.add_post('/api/restart-station', self.restart_station)
        app.router.add_get('/api/station-status/{station_id}', self.get_station_status)
