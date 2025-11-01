"""
API для запроса уровня громкости голосового вещания
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from datetime import datetime

from models.station import Station
from handlers.query_voice_volume import QueryVoiceVolumeHandler
from utils.centralized_logger import get_logger


class QueryVoiceVolumeAPI:
    """API для работы с запросами уровня громкости"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.voice_volume_handler = QueryVoiceVolumeHandler(db_pool, connection_manager)
        self.logger = get_logger('query_voice_volume_api')
    
    async def query_voice_volume(self, request: Request) -> Response:
        """
        Запрашивает уровень громкости станции
        POST /api/query-voice-volume
        """
        try:
            # Получаем данные из запроса
            data = await request.json()
            station_id = data.get('station_id')
            
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
            
            # Отправляем запрос уровня громкости
            result = await self.voice_volume_handler.send_voice_volume_request(station_id)
            
            if result['success']:
                return web.json_response({
                    'success': True,
                    'message': result['message'],
                    'station_box_id': result['station_box_id'],
                    'packet_hex': result['packet_hex']
                })
            else:
                # Логируем ошибку
                self.logger.error(f"API: Ошибка запроса уровня громкости для станции {station_id}: {result['error']}")
                
                return web.json_response({
                    'success': False,
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            error_msg = f"Ошибка API запроса уровня громкости: {str(e)}"
            self.logger.error(error_msg)
            
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=500)
    
    async def get_voice_volume_data(self, request: Request) -> Response:
        """
        Получает данные о громкости станции из кэша соединения
        GET /api/query-voice-volume/station/{station_id}
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
            
            # Проверяем, есть ли данные о громкости
            if not hasattr(connection, 'voice_volume_data') or not connection.voice_volume_data:
                return web.json_response({
                    'success': False,
                    'error': 'Данные о громкости не найдены. Сначала запросите уровень громкости.'
                }, status=404)
            
            # Возвращаем данные о громкости
            voice_volume_data = connection.voice_volume_data
            
            return web.json_response({
                'success': True,
                'station_id': station_id,
                'station_box_id': station.box_id,
                'voice_volume': voice_volume_data
            })
            
        except ValueError:
            return web.json_response({
                'success': False,
                'error': 'Неверный формат station_id'
            }, status=400)
        except Exception as e:
            error_msg = f"Ошибка получения данных о громкости: {str(e)}"
            self.logger.error(error_msg)
            
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=500)
    
    
