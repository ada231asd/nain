"""
Middleware для аутентификации JWT
"""
import jwt
import json
from aiohttp import web
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import os


JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

def jwt_middleware(handler):
    """
    Декоратор для проверки JWT токена
    """

    async def wrapper(self, request: web.Request, *args, **kwargs) -> web.Response:
        try:
            # Получаем токен из заголовка Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return web.json_response({
                    'error': 'Отсутствует заголовок Authorization'
                }, status=401)
            
            # Проверяем формат Bearer token
            if not auth_header.startswith('Bearer '):
                return web.json_response({
                    'error': 'Неверный формат токена. Используйте Bearer <token>'
                }, status=401)
            
            # Извлекаем токен
            token = auth_header[7:]  
            
            if not token:
                return web.json_response({
                    'error': 'Пустой токен'
                }, status=401)
            
            # Декодируем JWT токен
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except jwt.ExpiredSignatureError:
                return web.json_response({
                    'error': 'Токен истек'
                }, status=401)
            except jwt.InvalidTokenError as e:
                return web.json_response({
                    'error': f'Неверный токен: {str(e)}'
                }, status=401)
            
            # Проверяем, что токен содержит необходимые поля
            if 'user_id' not in payload or 'phone_e164' not in payload:
                return web.json_response({
                    'error': 'Неверная структура токена'
                }, status=401)
            
            # Добавляем информацию о пользователе в запрос
            request['user'] = {
                'user_id': payload['user_id'],
                'username': payload.get('phone_e164', 'unknown'),
                'role': payload.get('role', 'user'),
                'exp': payload.get('exp')
            }
            
            # Вызываем оригинальный обработчик
            if args or kwargs:
                return await handler(self, request, *args, **kwargs)
            return await handler(self, request)
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка аутентификации: {str(e)}'
            }, status=500)
    
    return wrapper

def create_jwt_token(user_data: Dict[str, Any], expires_hours: int = 24) -> str:
#  создание токена для пользователя
    # Добавляем время истечения
    from utils.time_utils import get_moscow_time
    now = get_moscow_time()
    exp_time = now.timestamp() + (expires_hours * 3600)
    
    payload = {
        'user_id': user_data['user_id'],
        'phone_e164': user_data.get('phone_e164', user_data.get('username', 'unknown')),
        'role': user_data.get('role', 'user'),
        'iat': now.timestamp(),
        'exp': exp_time
    }
    
    # Создаем токен
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt_token(token: str) -> Dict[str, Any]:
    # проверка токена
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def get_user_from_token(token: str) -> Dict[str, Any]:
  # извлечение информации о пользователе из токена
    try:
        payload = verify_jwt_token(token)
        return {
            'user_id': payload['user_id'],
            'username': payload.get('phone_e164', 'unknown'),
            'role': payload.get('role', 'user'),
            'exp': payload.get('exp')
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def is_token_expired(token: str) -> bool:
    # проверка истечения токена
    try:
        payload = verify_jwt_token(token)
        exp_time = payload.get('exp', 0)
        from utils.time_utils import moscow_timestamp
        current_time = moscow_timestamp()
        return current_time >= exp_time
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return True

def refresh_jwt_token(token: str, expires_hours: int = 24) -> str:
    # Декодируем старый токен
    payload = verify_jwt_token(token)
    
    # Создаем новый токен с теми же данными
    user_data = {
        'user_id': payload['user_id'],
        'phone_e164': payload.get('phone_e164', 'unknown'),
        'role': payload.get('role', 'user')
    }
    
    return create_jwt_token(user_data, expires_hours)

@web.middleware
async def jwt_aiohttp_middleware(request, handler):

    try:
        # Получаем токен из заголовка Authorization
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return web.json_response({
                'error': 'Отсутствует заголовок Authorization'
            }, status=401)
        
        # Проверяем формат Bearer token
        if not auth_header.startswith('Bearer '):
            return web.json_response({
                'error': 'Неверный формат токена. Используйте Bearer <token>'
            }, status=401)
        
        # Извлекаем токен
        token = auth_header[7:]  # Убираем "Bearer "
        
        if not token:
            return web.json_response({
                'error': 'Пустой токен'
            }, status=401)
        
        # Декодируем JWT токен
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return web.json_response({
                'error': 'Токен истек'
            }, status=401)
        except jwt.InvalidTokenError as e:
            return web.json_response({
                'error': f'Неверный токен: {str(e)}'
            }, status=401)
        
        # Проверяем, что токен содержит необходимые поля
        if 'user_id' not in payload or 'phone_e164' not in payload:
            return web.json_response({
                'error': 'Неверная структура токена'
            }, status=401)
        
        # Добавляем информацию о пользователе в запрос
        request['user'] = {
            'user_id': payload['user_id'],
            'username': payload.get('phone_e164', 'unknown'),
            'role': payload.get('role', 'user'),
            'exp': payload.get('exp')
        }
        
        # Вызываем следующий обработчик
        return await handler(request)
        
    except Exception as e:
        return web.json_response({
            'error': f'Ошибка аутентификации: {str(e)}'
        }, status=500)
