"""
API для запроса адреса сервера
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
import logging
import os
from datetime import datetime

from models.station import Station
from handlers.query_server_address import QueryServerAddressHandler
from utils.auth_middleware import jwt_middleware


class QueryServerAddressAPI:
    """API для работы с запросами адреса сервера"""
    
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
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Администратор {user_id} запросил адрес сервера станции.")
        
        try:
            data = await request.json()
            station_id = data.get('station_id')
            
            if not station_id:
                self.logger.warning(f"Администратор {user_id}: Не указан station_id для запроса адреса сервера.")
                return web.json_response({
                    'success': False,
                    'error': 'Не указан ID станции'
                }, status=400)
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                self.logger.warning(f"Администратор {user_id}: Станция с ID {station_id} не найдена.")
                return web.json_response({
                    'success': False,
                    'error': f'Станция с ID {station_id} не найдена'
                }, status=404)
            
            # Отправляем запрос адреса сервера
            result = await self.query_server_address_handler.send_query_server_address_request(station_id)
            
            if result['success']:
                self.logger.info(f"Администратор {user_id} успешно отправил запрос адреса сервера на станцию {station_id}.")
                return web.json_response({
                    'success': True,
                    'message': result['message'],
                    'station_box_id': result['station_box_id'],
                    'packet_hex': result.get('packet_hex')
                })
            else:
                self.logger.error(f"Администратор {user_id}: Ошибка отправки запроса адреса сервера на станцию {station_id}: {result['error']}")
                return web.json_response({
                    'success': False,
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            self.logger.error(f"Администратор {user_id}: Непредвиденная ошибка при запросе адреса сервера: {e}", exc_info=True)
            return web.json_response({
                'success': False,
                'error': f"Внутренняя ошибка сервера: {e}"
            }, status=500)
    
    @jwt_middleware
    async def get_server_address(self, request: Request) -> Response:
        """
        Получает сохраненный адрес сервера станции
        GET /api/query-server-address/station/{station_id}
        """
        user_id = request['user']['user_id']
        station_id = request.match_info.get('station_id')
        self.logger.info(f"Администратор {user_id} запросил сохраненный адрес сервера станции {station_id}.")
        
        if not station_id:
            return web.json_response({
                "success": False,
                "error": "Не указан ID станции"
            }, status=400)
        
        try:
            station_id = int(station_id)
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    "success": False,
                    "error": "Станция не найдена"
                }, status=404)
            
            # Получаем адрес сервера из базы данных
            result = await self.query_server_address_handler.get_station_server_address(station_id)
            
            if result["success"]:
                return web.json_response({
                    "success": True,
                    "station": {
                        "station_id": result["station_id"],
                        "box_id": result["box_id"],
                        "server_address": result["server_address"],
                        "server_ports": result["server_ports"],
                        "heartbeat_interval": result["heartbeat_interval"],
                        "server_address_updated_at": result["server_address_updated_at"],
                        "has_server_address": result["has_server_address"]
                    }
                })
            else:
                return web.json_response({
                    "success": False,
                    "error": result["error"]
                }, status=500)
                
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный формат ID станции"
            }, status=400)
        except Exception as e:
            self.logger.error(f"Ошибка получения адреса сервера станции {station_id}: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": f"Внутренняя ошибка сервера: {e}"
            }, status=500)
    
    @jwt_middleware
    async def get_server_address_logs(self, request: Request) -> Response:
        """
        Получает логи запросов адреса сервера
        GET /api/query-server-address/logs
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Администратор {user_id} запросил логи адреса сервера.")
        
        log_file_path = 'logs/query_server_address.log'
        logs = []
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    if line.strip():
                        parts = line.split(' - ', 2)
                        if len(parts) == 3:
                            logs.append({
                                'timestamp': parts[0],
                                'level': parts[1],
                                'message': parts[2].strip()
                            })
                        else:
                            logs.append({'message': line.strip()})
        except FileNotFoundError:
            logs = [{'message': 'Файл логов адреса сервера не найден'}]
        except Exception as e:
            self.logger.error(f"Ошибка чтения логов адреса сервера: {e}", exc_info=True)
            logs = [{'message': f'Ошибка чтения логов: {e}'}]
        
        return web.json_response({'logs': logs})
