"""
API endpoints для работы с повербанками и их статусами
"""
import aiomysql
from aiohttp import web
from aiohttp.web import Request, Response
from typing import Dict, Any
from models.powerbank_status import PowerbankStatus
from utils.json_utils import serialize_for_json
from utils.centralized_logger import get_logger


class PowerbankStatusAPI:
    """API для работы со статусами повербанков"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.powerbank_status = PowerbankStatus(db_pool)
    
    async def get_powerbanks_with_status(self, request: Request) -> Response:
        """GET /api/powerbanks/status - Получить повербанки с их статусами"""
        try:
            logger = get_logger('powerbank_status_api')
            
            # Получаем параметры запроса
            status_filter = request.query.get('status')  # 'in_station', 'in_use', 'not_returned'
            org_unit_id = request.query.get('org_unit_id')
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 50))
            
            # Валидация параметров
            if status_filter and status_filter not in ['in_station', 'in_use', 'not_returned']:
                return web.json_response({
                    "success": False,
                    "error": "Некорректный статус. Доступные: in_station, in_use, not_returned"
                }, status=400)
            
            if org_unit_id:
                try:
                    org_unit_id = int(org_unit_id)
                except ValueError:
                    return web.json_response({
                        "success": False,
                        "error": "org_unit_id должен быть числом"
                    }, status=400)
            
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 50
            
            # Получаем данные
            powerbanks, total = await self.powerbank_status.get_powerbanks_with_status(
                status_filter=status_filter,
                org_unit_id=org_unit_id,
                page=page,
                limit=limit
            )
            
            # Вычисляем пагинацию
            total_pages = (total + limit - 1) // limit
            
            return web.json_response(serialize_for_json({
                "success": True,
                "data": powerbanks,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters": {
                    "status": status_filter,
                    "org_unit_id": org_unit_id
                }
            }))
            
        except Exception as e:
            logger = get_logger('powerbank_status_api')
            logger.error(f"Ошибка получения повербанков со статусами: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_powerbank_status_summary(self, request: Request) -> Response:
        """GET /api/powerbanks/status/summary - Получить сводку по статусам повербанков"""
        try:
            logger = get_logger('powerbank_status_api')
            
            # Получаем параметры запроса
            org_unit_id = request.query.get('org_unit_id')
            
            if org_unit_id:
                try:
                    org_unit_id = int(org_unit_id)
                except ValueError:
                    return web.json_response({
                        "success": False,
                        "error": "org_unit_id должен быть числом"
                    }, status=400)
            
            # Получаем сводку
            summary = await self.powerbank_status.get_powerbank_status_summary(org_unit_id)
            
            return web.json_response(serialize_for_json({
                "success": True,
                "data": summary,
                "filters": {
                    "org_unit_id": org_unit_id
                }
            }))
            
        except Exception as e:
            logger = get_logger('powerbank_status_api')
            logger.error(f"Ошибка получения сводки по статусам: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_powerbank_by_id(self, request: Request) -> Response:
        """GET /api/powerbanks/{powerbank_id}/status - Получить конкретный повербанк со статусом"""
        try:
            logger = get_logger('powerbank_status_api')
            
            powerbank_id = int(request.match_info['powerbank_id'])
            
            # Получаем данные повербанка
            powerbank = await self.powerbank_status.get_powerbank_by_id(powerbank_id)
            
            if not powerbank:
                return web.json_response({
                    "success": False,
                    "error": "Повербанк не найден"
                }, status=404)
            
            return web.json_response(serialize_for_json({
                "success": True,
                "data": powerbank
            }))
            
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Некорректный ID повербанка"
            }, status=400)
        except Exception as e:
            logger = get_logger('powerbank_status_api')
            logger.error(f"Ошибка получения повербанка {powerbank_id}: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты API для статусов повербанков"""
        
        # Powerbank status routes - используем более специфичные пути чтобы избежать конфликтов
        app.router.add_get('/api/powerbanks-status', self.get_powerbanks_with_status)
        app.router.add_get('/api/powerbanks-status/summary', self.get_powerbank_status_summary)
        app.router.add_get('/api/powerbanks-status/{powerbank_id}', self.get_powerbank_by_id)
        
        # Обратная совместимость - старые маршруты (должны быть после новых)
        app.router.add_get('/api/powerbanks/status', self.get_powerbanks_with_status)
        app.router.add_get('/api/powerbanks/status/summary', self.get_powerbank_status_summary)
        app.router.add_get('/api/powerbanks/{powerbank_id}/status', self.get_powerbank_by_id)
