"""
HTTP endpoints для отчетов об аномалиях слотов
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List

from api.slot_abnormal_report_api import SlotAbnormalReportAPI


class SlotAbnormalReportEndpoints:
    """HTTP endpoints для отчетов об аномалиях слотов"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.abnormal_report_api = SlotAbnormalReportAPI(db_pool, connection_manager)
    
    async def get_station_abnormal_reports(self, request: Request) -> Response:
        """GET /api/slot-abnormal-reports/stations/{station_id} - Получить отчеты об аномалиях слотов станции"""
        try:
            station_id = int(request.match_info['station_id'])
            limit = int(request.query.get('limit', 50))
            
            if limit < 1 or limit > 200:
                return web.json_response({
                    "success": False,
                    "error": "limit должен быть от 1 до 200"
                }, status=400)
            
            result = await self.abnormal_report_api.get_station_abnormal_reports(station_id, limit)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции или limit"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_all_abnormal_reports(self, request: Request) -> Response:
        """GET /api/slot-abnormal-reports - Получить все отчеты об аномалиях слотов"""
        try:
            limit = int(request.query.get('limit', 100))
            
            if limit < 1 or limit > 500:
                return web.json_response({
                    "success": False,
                    "error": "limit должен быть от 1 до 500"
                }, status=400)
            
            result = await self.abnormal_report_api.get_all_abnormal_reports(limit)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный limit"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_abnormal_reports_statistics(self, request: Request) -> Response:
        """GET /api/slot-abnormal-reports/statistics - Получить статистику отчетов об аномалиях слотов"""
        try:
            result = await self.abnormal_report_api.get_abnormal_reports_statistics()
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_abnormal_reports_by_event_type(self, request: Request) -> Response:
        """GET /api/slot-abnormal-reports/event-type/{event_type} - Получить отчеты об аномалиях по типу события"""
        try:
            event_type = request.match_info['event_type']  # Оставляем как строку
            limit = int(request.query.get('limit', 50))
            
            if limit < 1 or limit > 200:
                return web.json_response({
                    "success": False,
                    "error": "limit должен быть от 1 до 200"
                }, status=400)
            
            result = await self.abnormal_report_api.get_abnormal_reports_by_event_type(event_type, limit)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный тип события или limit"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_abnormal_reports_by_date_range(self, request: Request) -> Response:
        """GET /api/slot-abnormal-reports/date-range - Получить отчеты об аномалиях за период времени"""
        try:
            start_date = request.query.get('start_date')
            end_date = request.query.get('end_date')
            limit = int(request.query.get('limit', 100))
            
            if not start_date or not end_date:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствуют обязательные параметры: start_date и end_date"
                }, status=400)
            
            if limit < 1 or limit > 500:
                return web.json_response({
                    "success": False,
                    "error": "limit должен быть от 1 до 500"
                }, status=400)
            
            result = await self.abnormal_report_api.get_abnormal_reports_by_date_range(start_date, end_date, limit)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный limit"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_abnormal_report(self, request: Request) -> Response:
        """DELETE /api/slot-abnormal-reports/{report_id} - Удалить отчет об аномалии"""
        try:
            report_id = int(request.match_info['report_id'])
            
            result = await self.abnormal_report_api.delete_abnormal_report(report_id)
            
            if result["success"]:
                return web.json_response(result)
            else:
                return web.json_response(result, status=400)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID отчета"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для отчетов об аномалиях слотов"""
        app.router.add_get('/api/slot-abnormal-reports/stations/{station_id}', self.get_station_abnormal_reports)
        app.router.add_get('/api/slot-abnormal-reports', self.get_all_abnormal_reports)
        app.router.add_get('/api/slot-abnormal-reports/statistics', self.get_abnormal_reports_statistics)
        app.router.add_get('/api/slot-abnormal-reports/event-type/{event_type}', self.get_abnormal_reports_by_event_type)
        app.router.add_get('/api/slot-abnormal-reports/date-range', self.get_abnormal_reports_by_date_range)
        app.router.add_delete('/api/slot-abnormal-reports/{report_id}', self.delete_abnormal_report)
