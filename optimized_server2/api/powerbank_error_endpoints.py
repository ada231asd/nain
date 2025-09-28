"""
HTTP endpoints для отчетов об ошибках повербанков
"""
from aiohttp import web
from typing import Dict, Any
import json

from api.powerbank_error_report_api import PowerbankErrorReportAPI


class PowerbankErrorEndpoints:
    """HTTP endpoints для отчетов об ошибках повербанков"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.error_report_api = PowerbankErrorReportAPI(db_pool)
    
    def setup_routes(self, app):
        """Настраивает маршруты для отчетов об ошибках"""
        
        # Создать отчет об ошибке повербанка
        async def report_powerbank_error(request):
            """Создать отчет об ошибке повербанка"""
            try:
                data = await request.json()
                
                print(f" PowerbankErrorEndpoints: Получен отчет об ошибке - {data}")
                
                if not data:
                    return web.json_response(
                        {"error": "Отсутствуют данные запроса", "success": False}, 
                        status=400
                    )
                
                # Извлекаем данные из запроса
                order_id = data.get('order_id')
                powerbank_id = data.get('powerbank_id')
                station_id = data.get('station_id')
                user_id = data.get('user_id')
                error_type = data.get('error_type')
                additional_notes = data.get('additional_notes')
                
                if not all([order_id, powerbank_id, station_id, user_id, error_type]):
                    return web.json_response(
                        {"error": "Отсутствуют обязательные поля", "success": False}, 
                        status=400
                    )
                
                # Создаем отчет об ошибке
                result = await self.error_report_api.report_powerbank_error(
                    order_id=int(order_id),
                    powerbank_id=int(powerbank_id),
                    station_id=int(station_id),
                    user_id=int(user_id),
                    error_type=error_type,
                    additional_notes=additional_notes
                )
                
                if result.get('success'):
                    return web.json_response(result)
                else:
                    return web.json_response(result, status=400)
                    
            except Exception as e:
                print(f" PowerbankErrorEndpoints: Ошибка сервера: {e}")
                return web.json_response(
                    {"error": f"Ошибка сервера: {str(e)}", "success": False}, 
                    status=500
                )
        
        # Регистрируем маршруты
        app.router.add_post('/powerbank-error-report', report_powerbank_error)
