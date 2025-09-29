"""
API для запроса адреса сервера станции
"""
from aiohttp import web
from aiohttp.web import Request, Response
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from handlers.query_server_address import QueryServerAddressHandler
from utils.auth_middleware import jwt_middleware


class QueryServerAddressAPI:
    """API для запроса адреса сервера станции"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.query_server_address_handler = QueryServerAddressHandler(db_pool, connection_manager)
        self.logger = get_logger('queryserveraddressapi')
    
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
    
    async def get_server_address_data(self, request: Request) -> Response:
        """
        Получает данные о адресе сервера станции из кэша соединения
        GET /api/query-server-address/station/{station_id}
        """
        try:
            station_id = request.match_info.get('station_id')
            
            if not station_id:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан station_id'
                }, status=400)
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    'success': False,
                    'error': f'Станция с ID {station_id} не найдена'
                }, status=404)
            
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(int(station_id))
            if not connection:
                return web.json_response({
                    'success': False,
                    'error': f'Станция {station.box_id} не подключена'
                }, status=404)
            
            # Проверяем, есть ли данные о адресе сервера
            if not hasattr(connection, 'server_address_data') or not connection.server_address_data:
                return web.json_response({
                    'success': False,
                    'error': 'Данные о адресе сервера не найдены. Сначала запросите адрес сервера.'
                }, status=404)
            
            # Возвращаем данные о адресе сервера
            server_address_data = connection.server_address_data
            
            return web.json_response({
                'success': True,
                'station_id': station_id,
                'station_box_id': station.box_id,
                'server_address': server_address_data
            })
            
        except ValueError:
            return web.json_response({
                'success': False,
                'error': 'Неверный формат station_id'
            }, status=400)
        except Exception as e:
            error_msg = f"Ошибка получения данных о адресе сервера: {str(e)}"
            self.logger.error(error_msg)
            
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=500)
    
    
