"""
API для запроса уровня громкости голосового вещания
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
import logging
import os
from datetime import datetime

from models.station import Station
from handlers.query_voice_volume import QueryVoiceVolumeHandler


class QueryVoiceVolumeAPI:
    """API для работы с запросами уровня громкости"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.voice_volume_handler = QueryVoiceVolumeHandler(db_pool, connection_manager)
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Настраивает логгер для записи в файл"""
        # Создаем папку для логов, если её нет
        os.makedirs('logs', exist_ok=True)
        
        logger = logging.getLogger('query_voice_volume_api')
        logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики
        logger.handlers.clear()
        
        # Создаем обработчик для записи в файл
        handler = logging.FileHandler('logs/query_voice_volume_api.log', encoding='utf-8')
        handler.setLevel(logging.INFO)
        
        # Создаем форматтер
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Добавляем обработчик к логгеру
        logger.addHandler(handler)
        
        return logger
    
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
                # Логируем успешный запрос
                self.logger.info(f"API: Запрос уровня громкости отправлен на станцию {station.box_id} (ID: {station_id})")
                
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
    
    async def get_voice_volume_logs(self, request: Request) -> Response:
        """
        Получает логи запросов уровня громкости
        GET /api/query-voice-volume/logs
        """
        try:
            # Читаем логи из файла
            log_file_path = 'logs/query_voice_volume.log'
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
