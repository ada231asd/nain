"""
API для запроса адреса сервера станции
"""
import logging
import os
from aiohttp import web
from aiohttp.web import Request, Response
from datetime import datetime

from models.station import Station
from handlers.query_server_address import QueryServerAddressHandler
from utils.auth_middleware import jwt_middleware


class QueryServerAddressAPI:
    """API для запроса адреса сервера станции"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.query_server_address_handler = QueryServerAddressHandler(db_pool, connection_manager)
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Настраивает логгер для записи в файл"""
        os.makedirs('logs', exist_ok=True)
        logger = logging.getLogger('query_server_address_api')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        handler = logging.FileHandler('logs/query_server_address_api.log', encoding='utf-8')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    @jwt_middleware
    async def query_server_address(self, request: Request) -> Response:
        """
        Запрашивает адрес сервера станции
        POST /api/query-server-address
        { "station_id": 123 }
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Администратор {user_id} запросил адрес сервера станции.")
        
        try:
            data = await request.json()
            station_id = data.get('station_id')
            
            if not station_id:
                self.logger.warning(f"Администратор {user_id}: Не указан station_id для запроса адреса сервера.")
                return web.json_response({"error": "Не указан ID станции"}, status=400)
            
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                self.logger.warning(f"Администратор {user_id}: Станция с ID {station_id} не найдена.")
                return web.json_response({"error": "Станция не найдена"}, status=404)
            
            response = await self.query_server_address_handler.send_query_server_address_request(station_id)
            
            if response["success"]:
                self.logger.info(f"Администратор {user_id} успешно отправил запрос адреса сервера на станцию {station_id}.")
                return web.json_response({
                    "success": True,
                    "message": response["message"],
                    "packet_hex": response.get("packet_hex")
                })
            else:
                self.logger.error(f"Администратор {user_id}: Ошибка отправки запроса адреса сервера на станцию {station_id}: {response['message']}")
                return web.json_response({"error": response["message"]}, status=500)
                
        except Exception as e:
            self.logger.error(f"Администратор {user_id}: Непредвиденная ошибка при запросе адреса сервера: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)
    
    @jwt_middleware
    async def get_station_server_address(self, request: Request) -> Response:
        """Получение кэшированного адреса сервера станции"""
        user_id = request['user']['user_id']
        self.logger.info(f"Администратор {user_id} запросил кэшированный адрес сервера станции.")
        
        try:
            station_id = int(request.match_info['station_id'])
            
            # Получаем данные из кэша
            result = await self.query_server_address_handler.get_station_server_address(station_id)
            
            if result['success']:
                self.logger.info(f"Администратор {user_id} получил адрес сервера станции {station_id}.")
                return web.json_response({
                    "success": True,
                    "station_id": station_id,
                    "server_address": result['server_address']
                })
            else:
                self.logger.warning(f"Администратор {user_id}: {result['error']} для станции {station_id}")
                return web.json_response({
                    "success": False,
                    "error": result['error']
                }, status=404)
                
        except ValueError:
            self.logger.warning(f"Администратор {user_id}: Неверный ID станции")
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции"
            }, status=400)
        except Exception as e:
            self.logger.error(f"Администратор {user_id}: Ошибка получения адреса сервера станции: {e}")
            return web.json_response({
                "success": False,
                "error": "Внутренняя ошибка сервера"
            }, status=500)
    
