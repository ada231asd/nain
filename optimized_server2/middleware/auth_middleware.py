"""
Middleware для авторизации
"""
from aiohttp import web
from aiohttp.web import Request, Response
from typing import Optional, Dict, Any
import jwt
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM
from models.user import User


class AuthMiddleware:
    """Middleware для проверки авторизации"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверяет JWT токен"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по токену"""
        payload = self.verify_jwt_token(token)
        if not payload:
            return None
        
        try:
            user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
            if not user:
                return None
            
            return {
                'user_id': user.user_id,
                'phone_e164': user.phone_e164,
                'email': user.email,
                'fio': user.fio,
                'status': user.status
            }
        except Exception:
            return None
    
    def create_auth_middleware(self):
        """Создает middleware для авторизации"""
        @web.middleware
        async def auth_middleware(request: Request, handler) -> Response:
            # Пропускаем CORS preflight запросы
            if request.method == 'OPTIONS':
                return await handler(request)
            
            # Пропускаем публичные endpoints
            public_paths = [
                '/api/auth/register',
                '/api/auth/login',
                '/api/invitations/',
                '/api/invitations/register',
                '/api/logos/'  # Логотипы должны быть доступны без авторизации
            ]
            
            # Проверяем, является ли путь публичным
            is_public = any(request.path.startswith(path) for path in public_paths)
            
            # Для публичных путей, которые требуют токен приглашения, проверяем его
            if request.path.startswith('/api/invitations/') and not request.path.endswith('/register'):
                # Для получения информации о приглашении токен не нужен
                if request.path.startswith('/api/invitations/') and request.method == 'GET':
                    return await handler(request)
            
            # Для остальных endpoints проверяем авторизацию
            if not is_public:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return web.json_response({
                        'error': 'Требуется авторизация'
                    }, status=401)
                
                token = auth_header.split(' ')[1]
                user = await self.get_user_from_token(token)
                
                if not user:
                    return web.json_response({
                        'error': 'Недействительный токен'
                    }, status=401)
                
                # Добавляем информацию о пользователе в request
                request['user'] = user
            
            return await handler(request)
        
        return auth_middleware
