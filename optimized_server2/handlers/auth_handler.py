"""
Обработчик авторизации и регистрации
"""
import json
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aiohttp import web
import aiomysql

from models.user import User, EmailService, VerificationCode
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, PASSWORD_MAX_LENGTH
from utils.centralized_logger import get_logger


class AuthHandler:
    """Обработчик авторизации"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.email_service = EmailService()
        self.logger = get_logger('auth_handler')
    
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
        """Регистрация пользователя"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['phone_e164', 'email']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = data['phone_e164']
            email = data['email']
            fio = data.get('fio')
            
            # Создаем пользователя
            user, password = await User.create_user(
                self.db_pool, phone_e164, email, fio
            )
            
            # Отправляем пароль на email
            email_sent = await self.email_service.send_password_email(
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
        """Авторизация пользователя с защитой от атак по стороннему каналу"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['phone_e164', 'password']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = data['phone_e164']
            password = data['password']
            
            # Защита от атак по стороннему каналу - проверяем длину пароля
            if len(password) > PASSWORD_MAX_LENGTH:
                self.logger.warning(f"🚨 ПОДОЗРИТЕЛЬНАЯ ПОПЫТКА: Пароль длиной {len(password)} символов для телефона {phone_e164}")
                return web.json_response({
                    'error': 'Неверный номер телефона, пароль или пользователь не подтвержден администратором'
                }, status=401)
            
            # Валидация пароля
            is_valid, error = User.validate_password(password)
            if not is_valid:
                self.logger.warning(f"🚨 НЕКОРРЕКТНЫЙ ПАРОЛЬ: {error} для телефона {phone_e164}")
                return web.json_response({
                    'error': 'Неверный номер телефона, пароль или пользователь не подтвержден администратором'
                }, status=401)
            
            # Аутентификация
            user = await User.authenticate(self.db_pool, phone_e164, password)
            
            if not user:
                return web.json_response({
                    'error': 'Неверный номер телефона, пароль или пользователь не подтвержден администратором'
                }, status=401)
            
            # Обновляем время последнего входа
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE app_user SET last_login_at = NOW() WHERE user_id = %s",
                        (user.user_id,)
                    )
            
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
    
    async def send_verification_code(self, request):
        """Отправка кода подтверждения"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['phone_e164', 'email']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = data['phone_e164']
            email = data['email']
            
            # Создаем код подтверждения
            verification_code = await VerificationCode.create_code(
                self.db_pool, phone_e164, email
            )
            
            # Отправляем код на email
            email_sent = await self.email_service.send_verification_code(
                email, verification_code.code
            )
            
            if not email_sent:
                return web.json_response({
                    'error': 'Ошибка отправки кода подтверждения'
                }, status=500)
            
            return web.json_response({
                'message': 'Код подтверждения отправлен на email'
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка отправки кода: {str(e)}'
            }, status=500)
    
    async def verify_code_and_login(self, request):
        """Проверка кода и авторизация"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['phone_e164', 'code']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            phone_e164 = data['phone_e164']
            code = data['code']
            
            # Проверяем код
            is_valid = await VerificationCode.verify_code(
                self.db_pool, phone_e164, code
            )
            
            if not is_valid:
                return web.json_response({
                    'error': 'Неверный или истекший код подтверждения'
                }, status=400)
            
            # Получаем пользователя
            user = await User.get_by_phone(self.db_pool, phone_e164)
            
            if not user:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
            # Создаем JWT токен
            token = self.create_jwt_token(user.user_id, user.phone_e164)
            
            return web.json_response({
                'message': 'Успешная авторизация',
                'token': token,
                'user': user.to_dict()
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка проверки кода: {str(e)}'
            }, status=500)
    
    async def get_user_profile(self, request):
        """Получение профиля пользователя"""
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
                self.db_pool, payload['phone_e164']
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
        """Обновление профиля пользователя"""
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
            
            # Получаем пользователя
            user = await User.get_by_phone(
                self.db_pool, payload['phone_e164']
            )
            
            if not user:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
            # Обновляем данные пользователя
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    update_fields = []
                    update_values = []
                    
                    if 'fio' in data:
                        update_fields.append('fio = %s')
                        update_values.append(data['fio'])
                    
                    if 'email' in data:
                        update_fields.append('email = %s')
                        update_values.append(data['email'])
                    
                    if update_fields:
                        update_values.append(user.user_id)
                        query = f"UPDATE app_user SET {', '.join(update_fields)} WHERE user_id = %s"
                        await cur.execute(query, update_values)
            
            # Получаем обновленного пользователя
            updated_user = await User.get_by_phone(
                self.db_pool, payload['phone_e164']
            )
            
            return web.json_response({
                'message': 'Профиль обновлен',
                'user': updated_user.to_dict()
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка обновления профиля: {str(e)}'
            }, status=500)
    
    async def get_pending_users(self, request):
        """Получение списка пользователей, ожидающих подтверждения (только для администраторов)"""
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
            
            # Проверяем, что пользователь - администратор
            current_user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
            if not current_user or current_user.role not in ['service_admin', 'group_admin']:
                return web.json_response({
                    'error': 'Недостаточно прав доступа. Требуется роль service_admin или group_admin'
                }, status=403)
            
            # Получаем пользователей со статусом pending
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT user_id, phone_e164, email, fio, status, created_at
                        FROM app_user 
                        WHERE status = 'pending'
                        ORDER BY created_at DESC
                    """)
                    users_data = await cur.fetchall()
            
            users = []
            for user_data in users_data:
                users.append({
                    'user_id': user_data['user_id'],
                    'phone_e164': user_data['phone_e164'],
                    'email': user_data['email'],
                    'fio': user_data['fio'],
                    'status': user_data['status'],
                    'created_at': user_data['created_at'].isoformat() if user_data['created_at'] else None
                })
            
            return web.json_response({
                'users': users
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения списка пользователей: {str(e)}'
            }, status=500)
    
    async def approve_user(self, request):
        """Подтверждение пользователя (только для администраторов)"""
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
            
            # Проверяем, что пользователь - администратор
            current_user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
            if not current_user or current_user.role not in ['service_admin', 'group_admin']:
                return web.json_response({
                    'error': 'Недостаточно прав доступа. Требуется роль service_admin или group_admin'
                }, status=403)
            
            data = await request.json()
            user_id = data.get('user_id')
            
            if not user_id:
                return web.json_response({
                    'error': 'ID пользователя обязателен'
                }, status=400)
            
            # Обновляем статус пользователя на active
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE app_user SET status = 'active' WHERE user_id = %s",
                        (user_id,)
                    )
                    
                    if cur.rowcount == 0:
                        return web.json_response({
                            'error': 'Пользователь не найден'
                        }, status=404)
            
            return web.json_response({
                'message': 'Пользователь подтвержден'
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка подтверждения пользователя: {str(e)}'
            }, status=500)
    
    async def reject_user(self, request):
        """Отклонение пользователя (только для администраторов)"""
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
            
            # Проверяем, что пользователь - администратор
            current_user = await User.get_by_phone(self.db_pool, payload['phone_e164'])
            if not current_user or current_user.role not in ['service_admin', 'group_admin']:
                return web.json_response({
                    'error': 'Недостаточно прав доступа. Требуется роль service_admin или group_admin'
                }, status=403)
            
            data = await request.json()
            user_id = data.get('user_id')
            
            if not user_id:
                return web.json_response({
                    'error': 'ID пользователя обязателен'
                }, status=400)
            
            # Обновляем статус пользователя на blocked
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE app_user SET status = 'blocked' WHERE user_id = %s",
                        (user_id,)
                    )
                    
                    if cur.rowcount == 0:
                        return web.json_response({
                            'error': 'Пользователь не найден'
                        }, status=404)
            
            return web.json_response({
                'message': 'Пользователь отклонен'
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка отклонения пользователя: {str(e)}'
            }, status=500)
