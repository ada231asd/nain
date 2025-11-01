"""
API для работы с приглашениями пользователей
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aiohttp import web
from aiohttp.web import Request, Response
import aiomysql
import json
from utils.json_utils import serialize_for_json
from utils.invitation_storage import invitation_storage


class InvitationAPI:
    """API для работы с приглашениями"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def generate_invitation_link(self, request: Request) -> Response:
        """POST /api/invitations/generate - Генерация ссылки-приглашения"""
        try:
            data = await request.json()
            
            # Проверяем авторизацию администратора
            user = request.get('user')
            
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверяем права администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для создания приглашений'
                }, status=403)
            
            # Валидация данных
            required_fields = ['org_unit_id', 'role']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            org_unit_id = data['org_unit_id']
            role = data['role']
            
            # Проверяем существование организационной единицы
            if not await self._check_org_unit_exists(org_unit_id):
                return web.json_response({
                    'error': 'Организационная единица не найдена'
                }, status=404)
            
            # Генерируем уникальный токен приглашения
            invitation_token = self._generate_invitation_token()
            
            # Сохраняем приглашение в хранилище (в памяти)
            success = invitation_storage.save_invitation(invitation_token, org_unit_id, role, user['user_id'])
            if not success:
                return web.json_response({
                    'error': 'Ошибка сохранения приглашения'
                }, status=500)
            
            # Формируем ссылку-приглашение
            # Используем настроенный URL фронтенда
            from config.settings import FRONTEND_URL
            base_url = FRONTEND_URL
            
            # URL-кодируем токен для безопасной передачи в URL
            from urllib.parse import quote
            encoded_token = quote(invitation_token, safe='')
            invitation_link = f"{base_url}/register?invitation={encoded_token}"
            
            return web.json_response({
                'success': True,
                'invitation_link': invitation_link,
                'invitation_token': invitation_token,
                'org_unit_id': org_unit_id,
                'role': role
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка создания приглашения: {str(e)}'
            }, status=500)
    
    async def get_invitation_info(self, request: Request) -> Response:
        """GET /api/invitations/{token} - Получение информации о приглашении"""
        try:
            invitation_token = request.match_info['token']
            
            # Получаем информацию о приглашении
            invitation_info = await self._get_invitation_info(invitation_token)
            
            if not invitation_info:
                return web.json_response({
                    'error': 'Приглашение не найдено или истекло'
                }, status=404)
            

            
            # Получаем информацию об организационной единице
            org_unit_info = await self._get_org_unit_info(invitation_info['org_unit_id'])
            
            return web.json_response({
                'success': True,
                'invitation': {
                    'token': invitation_token,
                'org_unit_id': invitation_info['org_unit_id'],
                'org_unit_name': org_unit_info['name'],
                'role': invitation_info['role']
                }
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения информации о приглашении: {str(e)}'
            }, status=500)
    
    async def register_with_invitation(self, request: Request) -> Response:
        """POST /api/invitations/register - Регистрация по приглашению"""
        try:
            data = await request.json()
            
            # Валидация данных
            required_fields = ['phone_e164', 'email', 'invitation_token']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            invitation_token = data['invitation_token']
            phone_e164 = data['phone_e164']
            email = data['email']
            fio = data.get('fio')
            
            # Получаем информацию о приглашении
            invitation_info = await self._get_invitation_info(invitation_token)
            
            if not invitation_info:
                return web.json_response({
                    'error': 'Приглашение не найдено'
                }, status=404)
            
            # Создаем пользователя с привязкой к группе
            user, password = await self._create_user_with_invitation(
                phone_e164, email, fio, invitation_info
            )
            
            # Отправляем пароль на email
            from utils.notification_service import notification_service
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
            
        except ValueError as e:
            return web.json_response({
                'error': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка регистрации по приглашению: {str(e)}'
            }, status=500)
    
    async def list_invitations(self, request: Request) -> Response:
        """GET /api/invitations - Список приглашений"""
        try:
            # Проверяем авторизацию администратора
            user = request.get('user')
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверяем права администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для просмотра приглашений'
                }, status=403)
            
            # Получаем список приглашений
            invitations = await self._get_invitations_list()
            
            return web.json_response({
                'success': True,
                'invitations': invitations
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения списка приглашений: {str(e)}'
            }, status=500)
    
    def _generate_invitation_token(self) -> str:
        """Генерирует уникальный токен приглашения"""
        return secrets.token_urlsafe(32)
    
    async def _check_admin_permissions(self, user_id: int) -> bool:
        """Проверяет права администратора"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT role FROM user_role 
                    WHERE user_id = %s AND role IN ('service_admin', 'group_admin', 'subgroup_admin')
                """, (user_id,))
                roles = await cur.fetchall()
                return len(roles) > 0
    
    async def _check_org_unit_exists(self, org_unit_id: int) -> bool:
        """Проверяет существование организационной единицы"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT org_unit_id FROM org_unit WHERE org_unit_id = %s
                """, (org_unit_id,))
                return await cur.fetchone() is not None
    
    
    async def _get_invitation_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о приглашении"""
        # Получаем приглашение из хранилища
        invitation = invitation_storage.get_invitation(token)
        
        if not invitation:
            return None
        
        return invitation
    
    async def _get_org_unit_info(self, org_unit_id: int) -> Dict[str, Any]:
        """Получает информацию об организационной единице"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT org_unit_id, name, unit_type, parent_org_unit_id 
                    FROM org_unit WHERE org_unit_id = %s
                """, (org_unit_id,))
                return await cur.fetchone()
    
    async def _create_user_with_invitation(self, phone_e164: str, email: str, fio: str, 
                                         invitation_info: Dict[str, Any]):
        """Создает пользователя с привязкой к группе из приглашения"""
        from models.user import User
        import bcrypt
        import secrets
        import string
        
        # Генерируем пароль
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Проверяем, не существует ли уже пользователь
                await cur.execute("""
                    SELECT user_id FROM app_user WHERE phone_e164 = %s OR email = %s
                """, (phone_e164, email))
                existing_user = await cur.fetchone()
                
                if existing_user:
                    raise ValueError("Пользователь с таким телефоном или email уже существует")
                
                # Создаем пользователя
                await cur.execute("""
                    INSERT INTO app_user (phone_e164, email, password_hash, fio, status, powerbank_limit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (phone_e164, email, password_hash, fio, 'pending', None))
                
                user_id = cur.lastrowid
                
                # Создаем роль пользователя
                await cur.execute("""
                    INSERT INTO user_role (user_id, org_unit_id, role, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, invitation_info['org_unit_id'], invitation_info['role'], datetime.now()))
                
                await conn.commit()
                
                user = User(
                    user_id=user_id,
                    phone_e164=phone_e164,
                    email=email,
                    password_hash=password_hash,
                    fio=fio,
                    status='pending',
                    created_at=datetime.now()
                )
                
                return user, password
    
    
    async def _get_invitations_list(self) -> list:
        """Получает список всех приглашений"""
        # Получаем список из хранилища
        invitations_raw = invitation_storage.get_all_invitations()
        
        invitations = []
        for invitation in invitations_raw:
            # Получаем информацию об организации
            org_unit_info = await self._get_org_unit_info(invitation['org_unit_id'])
            
            # Получаем информацию о создателе
            created_by_name = None
            if 'created_by' in invitation:
                user_info = await self._get_user_info(invitation['created_by'])
                if user_info:
                    created_by_name = user_info.get('fio', 'Unknown')
            
            invitations.append({
                'token': invitation['token'],
                'org_unit_id': invitation['org_unit_id'],
                'org_unit_name': org_unit_info.get('name', 'Unknown') if org_unit_info else 'Unknown',
                'role': invitation['role'],
                'used': invitation.get('used', False),
                'created_by': invitation.get('created_by'),
                'created_by_name': created_by_name,
                'created_at': invitation.get('created_at', '')
            })
        
        return invitations
    
    async def _get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT user_id, phone_e164, email, fio, status 
                    FROM app_user WHERE user_id = %s
                """, (user_id,))
                return await cur.fetchone()