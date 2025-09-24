"""
API для установки адреса сервера
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
import logging
import os
from datetime import datetime

from models.station import Station
from handlers.set_server_address import SetServerAddressHandler


class SetServerAddressAPI:
    """API для работы с установкой адреса сервера"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.set_server_address_handler = SetServerAddressHandler(db_pool, connection_manager)
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Настраивает логгер для записи в файл"""
        # Создаем папку для логов, если её нет
        os.makedirs('logs', exist_ok=True)
        
        logger = logging.getLogger('set_server_address_api')
        logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики
        logger.handlers.clear()
        
        # Создаем обработчик для записи в файл
        handler = logging.FileHandler('logs/set_server_address_api.log', encoding='utf-8')
        handler.setLevel(logging.INFO)
        
        # Создаем форматтер
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Добавляем обработчик к логгеру
        logger.addHandler(handler)
        
        return logger
    
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
                # Логируем успешный запрос
                self.logger.info(f"API: Установка адреса сервера отправлена на станцию {station.box_id} (ID: {station_id}) | "
                               f"Адрес: {server_address}:{server_port} | Heartbeat: {heartbeat_interval}")
                
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
    
    async def get_set_server_address_logs(self, request: Request) -> Response:
        """
        Получает логи установки адреса сервера
        GET /api/set-server-address/logs
        """
        try:
            # Читаем логи из файла
            log_file_path = 'logs/set_server_address.log'
            logs = []
            
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Берем последние 50 строк
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    
                    for line in recent_lines:
                        if line.strip():
                            logs.append({
                                'timestamp': line.split(' - ')[0] if ' - ' in line else '',
                                'level': line.split(' - ')[1] if ' - ' in line else '',
                                'message': ' - '.join(line.split(' - ')[2:]).strip() if ' - ' in line else line.strip()
                            })
            except FileNotFoundError:
                logs = [{'message': 'Файл логов не найден'}]
            
            return web.json_response({
                'logs': logs
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения логов: {str(e)}'
            }, status=500)

