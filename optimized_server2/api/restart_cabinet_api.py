"""
API для команды перезагрузки кабинета
"""
from aiohttp import web
from handlers.restart_cabinet import RestartCabinetHandler
from handlers.auth_handler import AuthHandler
from models.user import User
from utils.centralized_logger import get_logger
from datetime import datetime


class RestartCabinetAPI:
    """API для команды перезагрузки кабинета"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.restart_handler = RestartCabinetHandler(db_pool, connection_manager)
        self.auth_handler = AuthHandler(db_pool)
        self.logger = get_logger('restart_cabinet_api')
    
    async def restart_cabinet(self, request):
        """Отправляет команду перезагрузки кабинета"""
        try:
            # Извлекаем токен из заголовка
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.json_response({
                    'error': 'Токен авторизации не предоставлен'
                }, status=401)
            
            token = auth_header.split(' ')[1]
            payload = self.auth_handler.verify_jwt_token(token)
            
            if not payload:
                return web.json_response({
                    'error': 'Недействительный токен'
                }, status=401)
            
            # Получаем пользователя
            user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
            if not user:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
            # Проверяем права доступа (только администраторы)
            if user.role not in ['service_admin', 'group_admin']:
                return web.json_response({
                    'error': 'Недостаточно прав доступа. Требуется роль service_admin или group_admin'
                }, status=403)
            
            # Получаем данные запроса
            data = await request.json()
            station_id = data.get('station_id')
            
            if not station_id:
                return web.json_response({
                    'error': 'ID станции обязателен'
                }, status=400)
            
            # Отправляем команду перезагрузки
            result = await self.restart_handler.send_restart_command(station_id, user.user_id)
            
            if result['success']:
                return web.json_response({
                    'message': result['message'],
                    'station_box_id': result['station_box_id'],
                    'packet_hex': result['packet_hex']
                })
            else:
                return web.json_response({
                    'error': result['error']
                }, status=400)
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка отправки команды перезагрузки: {str(e)}'
            }, status=500)
    
