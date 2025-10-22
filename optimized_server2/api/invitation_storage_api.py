"""
API для работы с хранилищем приглашений
"""
from datetime import datetime
from typing import Optional, Dict, Any
from aiohttp import web
from aiohttp.web import Request, Response
import aiomysql
import json
from utils.invitation_storage import invitation_storage


class InvitationStorageAPI:
    """API для работы с хранилищем приглашений"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def store_invitation(self, request: Request) -> Response:
        """POST /api/invitations/store - Сохранение приглашения в хранилище"""
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
            required_fields = ['token', 'org_unit_id', 'role']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        'error': f'Поле {field} обязательно'
                    }, status=400)
            
            token = data['token']
            org_unit_id = data['org_unit_id']
            role = data['role']
            
            # Проверяем существование организационной единицы
            if not await self._check_org_unit_exists(org_unit_id):
                return web.json_response({
                    'error': 'Организационная единица не найдена'
                }, status=404)
            
            # Сохраняем приглашение в хранилище
            success = invitation_storage.save_invitation(
                token, org_unit_id, role, user['user_id']
            )
            
            if not success:
                return web.json_response({
                    'error': 'Ошибка сохранения приглашения'
                }, status=500)
            
            return web.json_response({
                'success': True,
                'message': 'Приглашение сохранено'
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка сохранения приглашения: {str(e)}'
            }, status=500)
    
    async def get_invitation(self, request: Request) -> Response:
        """GET /api/invitations/storage/{token} - Получение приглашения из хранилища"""
        try:
            token = request.match_info['token']
            
            # Получаем приглашение из хранилища
            invitation = invitation_storage.get_invitation(token)
            
            if not invitation:
                return web.json_response({
                    'error': 'Приглашение не найдено или истекло'
                }, status=404)
            
            # Получаем информацию об организационной единице
            org_unit_info = await self._get_org_unit_info(invitation['org_unit_id'])
            
            return web.json_response({
                'success': True,
                'invitation': {
                    'token': invitation['token'],
                    'org_unit_id': invitation['org_unit_id'],
                    'org_unit_name': org_unit_info['name'],
                    'role': invitation['role'],
                    'created_at': invitation['created_at'],
                    'used': invitation.get('used', False)
                }
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения приглашения: {str(e)}'
            }, status=500)
    
    async def get_statistics(self, request: Request) -> Response:
        """GET /api/invitations/storage/statistics - Статистика по приглашениям"""
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
                    'error': 'Недостаточно прав для просмотра статистики'
                }, status=403)
            
            stats = invitation_storage.get_statistics()
            
            return web.json_response({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            return web.json_response({
                'error': f'Ошибка получения статистики: {str(e)}'
            }, status=500)
    
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
    
    async def _get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT user_id, phone_e164, email, fio, status 
                    FROM app_user WHERE user_id = %s
                """, (user_id,))
                return await cur.fetchone()
    
    async def _get_org_unit_info(self, org_unit_id: int) -> Dict[str, Any]:
        """Получает информацию об организационной единице"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT org_unit_id, name, unit_type, parent_org_unit_id 
                    FROM org_unit WHERE org_unit_id = %s
                """, (org_unit_id,))
                return await cur.fetchone()

