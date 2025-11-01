"""
API для установки адреса сервера
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from handlers.set_server_address import SetServerAddressHandler


class SetServerAddressAPI:
    """API для работы с установкой адреса сервера"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.set_server_address_handler = SetServerAddressHandler(db_pool, connection_manager)
        self.logger = get_logger('setserveraddressapi')
    
    async def set_server_address(self, request: Request) -> Response:
        """
        Устанавливает адрес сервера для станции
        POST /api/set-server-address
        """
        try:
            # Получаем данные из запроса
            data = await request.json()
            station_id = data.get('station_id')
            server_address = data.get('server_address')
            server_port = data.get('server_port')
            heartbeat_interval = data.get('heartbeat_interval', 30)
            
            if not station_id:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан station_id'
                }, status=400)
            
            if not server_address:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан server_address'
                }, status=400)
            
            if not server_port:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан server_port'
                }, status=400)
            
            # Проверяем корректность интервала heartbeat
            if not (1 <= heartbeat_interval <= 255):
                return web.json_response({
                    'success': False,
                    'error': f'Интервал heartbeat должен быть от 1 до 255, получен: {heartbeat_interval}'
                }, status=400)
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    'success': False,
                    'error': f'Станция с ID {station_id} не найдена'
                }, status=404)
            
            # Отправляем запрос установки адреса сервера
            result = await self.set_server_address_handler.send_set_server_address_request(
                station_id, server_address, server_port, heartbeat_interval
            )
            
            if result['success']:
                return web.json_response({
                    'success': True,
                    'message': result['message'],
                    'station_box_id': result['station_box_id'],
                    'server_address': result['server_address'],
                    'server_port': result['server_port'],
                    'heartbeat_interval': result['heartbeat_interval'],
                    'packet_hex': result['packet_hex']
                })
            else:
                # Логируем ошибку
                self.logger.error(f"API: Ошибка установки адреса сервера для станции {station_id}: {result['error']}")
                
                return web.json_response({
                    'success': False,
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            error_msg = f"Ошибка API установки адреса сервера: {str(e)}"
            self.logger.error(error_msg)
            
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=500)
    

