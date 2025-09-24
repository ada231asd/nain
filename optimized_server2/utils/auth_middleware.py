"""
Middleware для аутентификации JWT
"""
import jwt
import json
from aiohttp import web
from typing import Dict, Any
from datetime import datetime, timezone
import os

# Секретный ключ для JWT (в продакшене должен быть в переменных окружения)
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
    """
    Создает JWT токен для пользователя
    
    Args:
        user_data: Данные пользователя (user_id, username, role)
        expires_hours: Время жизни токена в часах
    
    Returns:
        JWT токен в виде строки
    """
    # Добавляем время истечения
    now = datetime.now(timezone.utc)
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
    """
    Проверяет и декодирует JWT токен
    
    Args:
        token: JWT токен
    
    Returns:
        Декодированные данные токена
    
    Raises:
        jwt.ExpiredSignatureError: Если токен истек
        jwt.InvalidTokenError: Если токен неверный
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def get_user_from_token(token: str) -> Dict[str, Any]:
    """
    Извлекает информацию о пользователе из токена
    
    Args:
        token: JWT токен
    
    Returns:
        Словарь с данными пользователя
    """
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
    """
    Проверяет, истек ли токен
    
    Args:
        token: JWT токен
    
    Returns:
        True если токен истек, False если действителен
    """
    try:
        payload = verify_jwt_token(token)
        exp_time = payload.get('exp', 0)
        current_time = datetime.now(timezone.utc).timestamp()
        return current_time >= exp_time
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return True

def refresh_jwt_token(token: str, expires_hours: int = 24) -> str:
    """
    Обновляет JWT токен
    
    Args:
        token: Старый JWT токен
        expires_hours: Время жизни нового токена в часах
    
    Returns:
        Новый JWT токен
    
    Raises:
        jwt.ExpiredSignatureError: Если старый токен истек
        jwt.InvalidTokenError: Если старый токен неверный
    """
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
    """
    Aiohttp middleware для проверки JWT токена
    """
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