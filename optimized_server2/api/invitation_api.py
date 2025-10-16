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
            
            # Сохраняем приглашение в БД (используем таблицу action_logs для хранения)
            await self._save_invitation(invitation_token, org_unit_id, role, user['user_id'])
            
            # Формируем ссылку-приглашение
            base_url = request.headers.get('Host', 'localhost:8000')
            invitation_link = f"http://{base_url}/register?invitation={invitation_token}"
            
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
            
            # Приглашения теперь постоянные, проверка срока действия не нужна
            
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
            
            # Приглашения теперь постоянные, проверка срока действия не нужна
            
            # Проверяем, не использовано ли уже приглашение
            if invitation_info['used']:
                return web.json_response({
                    'error': 'Приглашение уже использовано'
                }, status=409)
            
            # Создаем пользователя с привязкой к группе
            user, password = await self._create_user_with_invitation(
                phone_e164, email, fio, invitation_info
            )
            
            # Отправляем пароль на email
            from services.notification_service import notification_service
            email_sent = await notification_service.send_password_email(
                email, password, fio, phone_e164
            )
            
            if not email_sent:
                return web.json_response({
                    'error': 'Ошибка отправки email с паролем'
                }, status=500)
            
            # Помечаем приглашение как использованное
            await self._mark_invitation_as_used(invitation_token)
            
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
    
    async def _save_invitation(self, token: str, org_unit_id: int, role: str, created_by: int):
        """Сохраняет приглашение в БД"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Сохраняем приглашение в action_logs с типом 'invitation_create'
                await cur.execute("""
                    INSERT INTO action_logs (user_id, action_type, entity_type, entity_id, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    created_by,
                    'invitation_create',
                    'system',
                    org_unit_id,
                    json.dumps({
                        'invitation_token': token,
                        'org_unit_id': org_unit_id,
                        'role': role,
                        'used': False
                    }),
                    datetime.now()
                ))
    
    async def _get_invitation_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о приглашении"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT description, created_at FROM action_logs 
                    WHERE action_type = 'invitation_create' 
                    AND description LIKE %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (f'%{token}%',))
                
                row = await cur.fetchone()
                if not row:
                    return None
                
                try:
                    invitation_data = json.loads(row['description'])
                    return invitation_data
                except (json.JSONDecodeError, ValueError):
                    return None
    
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
                """, (phone_e164, email, password_hash, fio, 'pending', 1))
                
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
    
    async def _mark_invitation_as_used(self, token: str):
        """Помечает приглашение как использованное"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Находим запись с приглашением
                await cur.execute("""
                    SELECT id, description FROM action_logs 
                    WHERE action_type = 'invitation_create' 
                    AND description LIKE %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (f'%{token}%',))
                
                row = await cur.fetchone()
                if row:
                    try:
                        invitation_data = json.loads(row[1])
                        invitation_data['used'] = True
                        
                        # Обновляем запись
                        await cur.execute("""
                            UPDATE action_logs 
                            SET description = %s 
                            WHERE id = %s
                        """, (json.dumps(invitation_data), row[0]))
                        
                        await conn.commit()
                    except (json.JSONDecodeError, ValueError):
                        pass
    
    async def _get_invitations_list(self) -> list:
        """Получает список всех приглашений"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT al.id, al.user_id, al.entity_id as org_unit_id, al.description, al.created_at,
                           ou.name as org_unit_name, u.fio as created_by_name
                    FROM action_logs al
                    LEFT JOIN org_unit ou ON al.entity_id = ou.org_unit_id
                    LEFT JOIN app_user u ON al.user_id = u.user_id
                    WHERE al.action_type = 'invitation_create'
                    ORDER BY al.created_at DESC
                """)
                
                rows = await cur.fetchall()
                invitations = []
                
                for row in rows:
                    try:
                        invitation_data = json.loads(row['description'])
                        
                        invitations.append({
                            'id': row['id'],
                            'token': invitation_data['invitation_token'],
                            'org_unit_id': row['org_unit_id'],
                            'org_unit_name': row['org_unit_name'],
                            'role': invitation_data['role'],
                            'used': invitation_data.get('used', False),
                            'created_by': row['user_id'],
                            'created_by_name': row['created_by_name'],
                            'created_at': row['created_at'].isoformat()
                        })
                    except (json.JSONDecodeError, ValueError):
                        continue
                
                return invitations