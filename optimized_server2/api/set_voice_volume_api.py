"""
API для установки уровня громкости голосового вещания
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from handlers.set_voice_volume import SetVoiceVolumeHandler


class SetVoiceVolumeAPI:
    """API для работы с установкой уровня громкости"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.set_voice_volume_handler = SetVoiceVolumeHandler(db_pool, connection_manager)
        self.logger = get_logger('setvoicevolumeapi')
    
    async def set_voice_volume(self, request: Request) -> Response:
        """
        Устанавливает уровень громкости станции
        POST /api/set-voice-volume
        """
        try:
            # Получаем данные из запроса
            data = await request.json()
            station_id = data.get('station_id')
            volume_level = data.get('volume_level')
            
            if not station_id:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан station_id'
                }, status=400)
            
            if volume_level is None:
                return web.json_response({
                    'success': False,
                    'error': 'Не указан volume_level'
                }, status=400)
            
            # Проверяем корректность уровня громкости
            if not (0 <= volume_level <= 15):
                return web.json_response({
                    'success': False,
                    'error': f'Уровень громкости должен быть от 0 до 15, получен: {volume_level}'
                }, status=400)
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    'success': False,
                    'error': f'Станция с ID {station_id} не найдена'
                }, status=404)
            
            # Отправляем запрос установки уровня громкости
            result = await self.set_voice_volume_handler.send_set_voice_volume_request(station_id, volume_level)
            
            if result['success']:
                return web.json_response({
                    'success': True,
                    'message': result['message'],
                    'station_box_id': result['station_box_id'],
                    'volume_level': result['volume_level'],
                    'packet_hex': result['packet_hex']
                })
            else:
                # Логируем ошибку
                self.logger.error(f"API: Ошибка установки уровня громкости для станции {station_id}: {result['error']}")
                
                return web.json_response({
                    'success': False,
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            error_msg = f"Ошибка API установки уровня громкости: {str(e)}"
            self.logger.error(error_msg)
            
            return web.json_response({
                'success': False,
                'error': error_msg
            }, status=500)
    

