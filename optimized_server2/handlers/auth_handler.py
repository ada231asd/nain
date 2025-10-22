"""
Обработчик авторизации и регистрации
"""
import json
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aiohttp import web
import aiomysql

from models.user import User
from models.action_log import ActionLog
from utils.notification_service import notification_service
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, PASSWORD_MAX_LENGTH
from utils.centralized_logger import get_logger
from utils.time_utils import get_moscow_time


class AuthHandler:
    """Обработчик авторизации"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
 
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
            invitation_token = data.get('invitation_token')
            
            # Если есть токен приглашения, регистрируем через приглашение
            if invitation_token:
                return await self._register_with_invitation(phone_e164, email, fio, invitation_token)
            
            # Обычная регистрация
            # Создаем пользователя
            user, password = await User.create_user(
                self.db_pool, phone_e164, email, fio
            )
            
            # Создаем роль пользователя по умолчанию (без привязки к группе)
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO user_role (user_id, role, org_unit_id)
                        VALUES (%s, 'user', NULL)
                    """, (user.user_id,))
                    await conn.commit()
            
            # Отправляем пароль на email с номером телефона
            email_sent = await notification_service.send_password_email(
                email, password, fio, phone_e164
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
    
    async def _register_with_invitation(self, phone_e164: str, email: str, fio: str, invitation_token: str):
        """Регистрация по приглашению"""
        try:
            from api.invitation_api import InvitationAPI
            invitation_api = InvitationAPI(self.db_pool)
            
            # Логируем полученный токен для отладки
            self.logger.info(f"🎫 Registration with invitation token: {invitation_token}")
            
            # Получаем информацию о приглашении
            invitation_info = await invitation_api._get_invitation_info(invitation_token)
            
            if not invitation_info:
                self.logger.warning(f"❌ Invitation not found for token: {invitation_token}")
                return web.json_response({
                    'error': 'Приглашение не найдено'
                }, status=404)
            
            # Приглашения могут использоваться неограниченное количество раз
            # Создаем пользователя с привязкой к группе
            user, password = await invitation_api._create_user_with_invitation(
                phone_e164, email, fio, invitation_info
            )
            
            # Отправляем пароль на email
            email_sent = await notification_service.send_password_email(
                email, password, fio, phone_e164
            )
            
            if not email_sent:
                return web.json_response({
                    'error': 'Ошибка отправки email с паролем'
                }, status=500)
            
            return web.json_response({
                'success': True,
                'message': 'Регистрация по приглашению прошла успешно. Пароль отправлен на email. Ожидает подтверждения администратора.',
                'user_id': user.user_id,
                'status': user.status,
                'org_unit_id': invitation_info['org_unit_id'],
                'role': invitation_info['role']
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка регистрации по приглашению: {str(e)}'
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
                self.logger.warning(f"ПОДОЗРИТЕЛЬНАЯ ПОПЫТКА: Пароль длиной {len(password)} символов для телефона {phone_e164}")
                return web.json_response({
                    'error': 'Неверный номер телефона, пароль или пользователь не подтвержден администратором'
                }, status=401)
            
            # Валидация пароля
            is_valid, error = User.validate_password(password)
            if not is_valid:
                self.logger.warning(f"НЕКОРРЕКТНЫЙ ПАРОЛЬ: {error} для телефона {phone_e164}")
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
                        "UPDATE app_user SET last_login_at = %s WHERE user_id = %s",
                        (get_moscow_time(), user.user_id)
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
            
            # Получаем организационную единицу пользователя
            org_unit_id = None
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT org_unit_id FROM user_role 
                        WHERE user_id = %s
                        LIMIT 1
                    """, (user.user_id,))
                    result = await cur.fetchone()
                    if result:
                        org_unit_id = result[0]
            
            user_dict = user.to_dict()
            user_dict['org_unit_id'] = org_unit_id
            
            return web.json_response({
                'user': user_dict
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
            
            # Получаем данные пользователя перед обновлением
            user_to_approve = await User.get_by_id(self.db_pool, user_id)
            if not user_to_approve:
                return web.json_response({
                    'error': 'Пользователь не найден'
                }, status=404)
            
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
            
            # Отправляем уведомление об одобрении
            try:
                email_sent = await notification_service.send_account_approved_email(
                    user_to_approve.email, 
                    user_to_approve.fio, 
                    user_to_approve.phone_e164
                )
                
                if email_sent:
                    return web.json_response({
                        'message': 'Пользователь подтвержден. Уведомление отправлено на email.'
                    })
                else:
                    return web.json_response({
                        'message': 'Пользователь подтвержден, но не удалось отправить уведомление на email.'
                    })
            except Exception as e:
                return web.json_response({
                    'message': f'Пользователь подтвержден, но ошибка отправки уведомления: {str(e)}'
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
    
    async def reset_email_service(self, request):
        """Сброс состояния email сервиса """
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
            
            # Сбрасываем состояние email сервиса
            notification_service.force_enable_email()
            
            return web.json_response({
                'message': 'Email сервис сброшен и включен',
                'email_enabled': notification_service.email_enabled
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка сброса email сервиса: {str(e)}'
            }, status=500)
