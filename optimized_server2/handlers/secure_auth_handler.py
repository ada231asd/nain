"""
Безопасный обработчик авторизации с защитой от атак
"""
import json
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aiohttp import web
import aiomysql
import bcrypt
import re

from models.user import User, VerificationCode
from utils.notification_service import notification_service
from utils.centralized_logger import get_logger
from utils.time_utils import get_moscow_time
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from middleware.input_validator import create_input_validator


class SecureAuthHandler:
    """Безопасный обработчик авторизации"""
    
    def __init__(self, secure_db):
        self.secure_db = secure_db
        self.input_validator = create_input_validator()
        self.logger = get_logger('secure_auth')
        
        # Паттерны для дополнительной валидации
        self.phone_pattern = re.compile(r'^\+[1-9]\d{1,14}$')
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def create_jwt_token(self, user_id: int, phone_e164: str) -> str:
        """Создает JWT токен"""
        payload = {
            'user_id': user_id,
            'phone_e164': phone_e164,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверяет JWT токен"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def register_user(self, request):
        """Регистрация пользователя с защитой"""
        try:
            data = await request.json()
            
            # Валидация входных данных
            validation_result = self.input_validator.validate_user_data(data)
            if validation_result['errors']:
                return web.json_response({
                    'error': 'Ошибки валидации: ' + ', '.join(validation_result['errors'])
                }, status=400)
            
            validated_data = validation_result['validated_data']
            
            # Дополнительная проверка обязательных полей
            required_fields = ['phone_e164', 'email']
            for field in required_fields:
                if field not in validated_data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = validated_data['phone_e164']
            email = validated_data['email']
            fio = validated_data.get('fio')
            
            # Проверяем, не существует ли уже пользователь
            existing_user = await self._check_existing_user(phone_e164, email)
            if existing_user:
                return web.json_response({
                    'error': 'Пользователь с таким телефоном или email уже существует'
                }, status=400)
            
            # Создаем пользователя
            user, password = await User.create_user(
                self.secure_db.db_pool, phone_e164, email, fio
            )
            
            # Отправляем пароль на email
            email_sent = await notification_service.send_password_email(
                email, password, fio
            )
            
            if not email_sent:
                return web.json_response({
                    'error': 'Ошибка отправки email с паролем'
                }, status=500)
            
            return web.json_response({
                'message': 'Пользователь зарегистрирован. Пароль отправлен на email. Ожидает подтверждения администратора.',
                'user_id': user.user_id,
                'status': user.status
            })
            
        except ValueError as e:
            return web.json_response({
                'error': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка регистрации: {str(e)}'
            }, status=500)
    
    async def login_user(self, request):
        """Авторизация пользователя с защитой"""
        try:
            data = await request.json()
            
            # Валидация входных данных
            validation_result = self.input_validator.validate_user_data(data)
            if validation_result['errors']:
                return web.json_response({
                    'error': 'Ошибки валидации: ' + ', '.join(validation_result['errors'])
                }, status=400)
            
            validated_data = validation_result['validated_data']
            
            # Дополнительная проверка обязательных полей
            required_fields = ['phone_e164', 'password']
            for field in required_fields:
                if field not in validated_data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = validated_data['phone_e164']
            password = validated_data['password']
            
            # Аутентификация
            user = await User.authenticate(self.secure_db.db_pool, phone_e164, password)
            
            if not user:
                return web.json_response({
                    'error': 'Неверный номер телефона, пароль или пользователь не подтвержден администратором'
                }, status=401)
            
            # Обновляем время последнего входа
            await self._update_last_login(user.user_id)
            
            # Создаем JWT токен
            token = self.create_jwt_token(user.user_id, user.phone_e164)
            
            return web.json_response({
                'message': 'Успешная авторизация',
                'token': token,
                'user': user.to_dict()
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка авторизации: {str(e)}'
            }, status=500)
    
    async def get_user_profile(self, request):
        """Получение профиля пользователя с защитой"""
        try:
            # Извлекаем токен из заголовка
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.json_response({
                    'error': 'Токен авторизации не предоставлен'
                }, status=401)
            
            token = auth_header.split(' ')[1]
            payload = self.verify_jwt_token(token)
            
            if not payload:
                return web.json_response({
                    'error': 'Недействительный токен'
                }, status=401)
            
            # Получаем пользователя
            user = await User.get_by_phone(
                self.secure_db.db_pool, payload['phone_e164']
            )
            
            if not user:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
            return web.json_response({
                'user': user.to_dict()
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения профиля: {str(e)}'
            }, status=500)
    
    async def update_user_profile(self, request):
        """Обновление профиля пользователя с защитой"""
        try:
            # Извлекаем токен из заголовка
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.json_response({
                    'error': 'Токен авторизации не предоставлен'
                }, status=401)
            
            token = auth_header.split(' ')[1]
            payload = self.verify_jwt_token(token)
            
            if not payload:
                return web.json_response({
                    'error': 'Недействительный токен'
                }, status=401)
            
            data = await request.json()
            
            # Валидация входных данных
            validation_result = self.input_validator.validate_user_data(data)
            if validation_result['errors']:
                return web.json_response({
                    'error': 'Ошибки валидации: ' + ', '.join(validation_result['errors'])
                }, status=400)
            
            validated_data = validation_result['validated_data']
            
            # Получаем пользователя
            user = await User.get_by_phone(
                self.secure_db.db_pool, payload['phone_e164']
            )
            
            if not user:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
            # Обновляем данные пользователя
            await self._update_user_data(user.user_id, validated_data)
            
            # Получаем обновленного пользователя
            updated_user = await User.get_by_phone(
                self.secure_db.db_pool, payload['phone_e164']
            )
            
            return web.json_response({
                'message': 'Профиль обновлен',
                'user': updated_user.to_dict()
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка обновления профиля: {str(e)}'
            }, status=500)
    
    async def _check_existing_user(self, phone_e164: str, email: str) -> bool:
        """Проверяет существование пользователя"""
        try:
            async with self.secure_db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT user_id FROM app_user WHERE phone_e164 = %s OR email = %s",
                        (phone_e164, email)
                    )
                    return await cur.fetchone() is not None
        except Exception:
            return False
    
    async def _update_last_login(self, user_id: int):
        """Обновляет время последнего входа"""
        try:
            await self.secure_db.execute_safe_update(
                "UPDATE app_user SET last_login_at = %s WHERE user_id = %s",
                (get_moscow_time(), user_id)
            )
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def _update_user_data(self, user_id: int, data: Dict[str, Any]):
        """Обновляет данные пользователя"""
        try:
            update_fields = []
            params = []
            
            allowed_fields = ['fio', 'email']
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if update_fields:
                params.append(user_id)
                query = f"UPDATE app_user SET {', '.join(update_fields)} WHERE user_id = %s"
                await self.secure_db.execute_safe_update(query, tuple(params))
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            raise

