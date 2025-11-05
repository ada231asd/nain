"""
HTTP endpoints для административных операций с повербанками
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List

from api.admin_powerbank_api import AdminPowerbankAPI


class AdminEndpoints:
    """HTTP endpoints для администратора"""
    
    def __init__(self, db_pool, connection_manager=None):
        self.db_pool = db_pool
        self.admin_api = AdminPowerbankAPI(db_pool, connection_manager)
    
    async def force_eject_powerbank(self, request: Request) -> Response:
        """POST /api/admin/force-eject-powerbank - принудительное извлечение повербанка"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['station_id', 'slot_number', 'admin_user_id']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            station_id = data['station_id']
            slot_number = data['slot_number']
            admin_user_id = data['admin_user_id']
            
            # Валидация типов данных
            try:
                station_id = int(station_id)
                slot_number = int(slot_number)
                admin_user_id = int(admin_user_id)
            except (ValueError, TypeError):
                return web.json_response({
                    "success": False,
                    "error": "station_id, slot_number и admin_user_id должны быть числами"
                }, status=400)
            
            # Получаем информацию о станции для валидации количества слотов
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    "success": False,
                    "error": "Станция не найдена"
                }, status=404)
            
            # Валидация диапазонов на основе реального количества слотов
            max_slots = station.slots_declared
            if slot_number < 1 or slot_number > max_slots:
                return web.json_response({
                    "success": False,
                    "error": f"slot_number должен быть от 1 до {max_slots}"
                }, status=400)
            
            result = await self.admin_api.force_eject_powerbank(
                station_id, slot_number, admin_user_id
            )
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def write_off_powerbank(self, request: Request) -> Response:
        """POST /api/admin/write-off-powerbank - списать повербанк у пользователя как утерянный 
        """
        try:
            data = await request.json()
            required = ['user_id', 'powerbank_id', 'admin_user_id']
            for f in required:
                if f not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {f}"
                    }, status=400)

            user_id = int(data['user_id'])
            powerbank_id = int(data['powerbank_id'])
            admin_user_id = int(data['admin_user_id'])
            note = data.get('note')

            result = await self.admin_api.write_off_powerbank_lost(user_id, powerbank_id, admin_user_id, note)

            return web.json_response(result, status=200 if result.get('success') else 400)
        except (ValueError, TypeError):
            return web.json_response({
                "success": False,
                "error": "user_id, powerbank_id и admin_user_id должны быть числами"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для администратора"""
        app.router.add_post('/api/admin/force-eject-powerbank', self.force_eject_powerbank)
        app.router.add_post('/api/admin/write-off-powerbank', self.write_off_powerbank)
