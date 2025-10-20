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
    
    async def get_unknown_powerbanks(self, request: Request) -> Response:
        """GET /api/admin/unknown-powerbanks - список повербанков со статусом unknown"""
        try:
            powerbanks = await self.admin_api.get_unknown_powerbanks()
            
            return web.json_response({
                "success": True,
                "data": powerbanks,
                "count": len(powerbanks)
            })
            
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def activate_powerbank(self, request: Request) -> Response:
        """POST /api/admin/activate-powerbank - активация повербанка"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['powerbank_id', 'admin_user_id']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            powerbank_id = data['powerbank_id']
            admin_user_id = data['admin_user_id']
            target_org_unit_id = data.get('target_org_unit_id')
            
            result = await self.admin_api.activate_powerbank(
                powerbank_id, admin_user_id, target_org_unit_id
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
    
    async def deactivate_powerbank(self, request: Request) -> Response:
        """POST /api/admin/deactivate-powerbank - деактивация повербанка"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['powerbank_id', 'admin_user_id']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            powerbank_id = data['powerbank_id']
            admin_user_id = data['admin_user_id']
            reason = data.get('reason', 'admin_deactivated')
            
            result = await self.admin_api.deactivate_powerbank(
                powerbank_id, admin_user_id, reason
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
    
    async def get_powerbank_status(self, request: Request) -> Response:
        """GET /api/admin/powerbank-status/{powerbank_id} - статус повербанка"""
        try:
            powerbank_id = int(request.match_info['powerbank_id'])
            
            result = await self.admin_api.get_powerbank_status(powerbank_id)
            
            if "error" in result:
                return web.json_response(result, status=404)
            else:
                return web.json_response({
                    "success": True,
                    "data": result
                })
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID повербанка"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def bulk_activate_powerbanks(self, request: Request) -> Response:
        """POST /api/admin/bulk-activate-powerbanks - массовая активация повербанков"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['powerbank_ids', 'admin_user_id']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            powerbank_ids = data['powerbank_ids']
            admin_user_id = data['admin_user_id']
            target_org_unit_id = data.get('target_org_unit_id')
            
            if not isinstance(powerbank_ids, list) or len(powerbank_ids) == 0:
                return web.json_response({
                    "success": False,
                    "error": "powerbank_ids должен быть непустым массивом"
                }, status=400)
            
            result = await self.admin_api.bulk_activate_powerbanks(
                powerbank_ids, admin_user_id, target_org_unit_id
            )
            
            return web.json_response(result)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_powerbank_statistics(self, request: Request) -> Response:
        """GET /api/admin/powerbank-statistics - статистика по повербанкам"""
        try:
            stats = await self.admin_api.get_powerbank_statistics()
            
            if "error" in stats:
                return web.json_response(stats, status=500)
            else:
                return web.json_response({
                    "success": True,
                    "data": stats
                })
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
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

        Body JSON: { user_id, powerbank_id, admin_user_id, note? }
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
        app.router.add_get('/api/admin/unknown-powerbanks', self.get_unknown_powerbanks)
        app.router.add_post('/api/admin/activate-powerbank', self.activate_powerbank)
        app.router.add_post('/api/admin/deactivate-powerbank', self.deactivate_powerbank)
        app.router.add_get('/api/admin/powerbank-status/{powerbank_id}', self.get_powerbank_status)
        app.router.add_post('/api/admin/bulk-activate-powerbanks', self.bulk_activate_powerbanks)
        app.router.add_get('/api/admin/powerbank-statistics', self.get_powerbank_statistics)
        app.router.add_post('/api/admin/force-eject-powerbank', self.force_eject_powerbank)
        app.router.add_post('/api/admin/write-off-powerbank', self.write_off_powerbank)
