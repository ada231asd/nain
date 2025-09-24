"""
HTTP endpoints для запроса ICCID SIM карт станций
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List

from api.query_iccid_api import QueryICCIDAPI


class QueryICCIDEndpoints:
    """HTTP endpoints для запроса ICCID SIM карт станций"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.iccid_api = QueryICCIDAPI(db_pool, connection_manager)
    
    async def query_station_iccid(self, request: Request) -> Response:
        """POST /api/iccid/stations/{station_id}/query - Запросить ICCID станции"""
        try:
            station_id = int(request.match_info['station_id'])
            
            result = await self.iccid_api.query_station_iccid(station_id)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
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
    
    async def get_station_iccid(self, request: Request) -> Response:
        """GET /api/iccid/stations/{station_id} - Получить ICCID станции"""
        try:
            station_id = int(request.match_info['station_id'])
            
            result = await self.iccid_api.get_station_iccid(station_id)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
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
        """Настраивает маршруты для запроса ICCID"""
        app.router.add_post('/api/iccid/stations/{station_id}/query', self.query_station_iccid)
        app.router.add_get('/api/iccid/stations/{station_id}', self.get_station_iccid)
