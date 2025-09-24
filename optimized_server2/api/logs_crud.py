"""
CRUD API для управления логами действий
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime, timedelta
from utils.json_utils import serialize_for_json


class LogsCRUD:
    """CRUD endpoints для логов действий"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def create_log_entry(self, action_type: str, description: str, user_id: int = None, 
                              entity_type: str = None, entity_id: int = None, 
                              additional_data: dict = None) -> int:
        """Создает запись в логе действий"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Добавляем дополнительные данные в описание
                    full_description = description
                    if additional_data:
                        additional_info = []
                        for key, value in additional_data.items():
                            additional_info.append(f"{key}: {value}")
                        if additional_info:
                            full_description += f" | {', '.join(additional_info)}"
                    
                    await cur.execute("""
                        INSERT INTO action_logs (user_id, action_type, entity_type, entity_id, description)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        action_type,
                        entity_type,
                        entity_id,
                        full_description
                    ))
                    
                    return cur.lastrowid
        except Exception as e:
            print(f"Ошибка создания лога: {e}")
            return None
    
    async def get_logs(self, request: Request) -> Response:
        """GET /api/logs - Получить список логов"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            action_type = request.query.get('action_type')
            entity_type = request.query.get('entity_type')
            user_id = request.query.get('user_id')
            days = int(request.query.get('days', 7))  # По умолчанию за последние 7 дней
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    # Фильтр по времени
                    where_conditions.append("al.created_at >= %s")
                    params.append(datetime.now() - timedelta(days=days))
                    
                    if action_type:
                        where_conditions.append("al.action_type = %s")
                        params.append(action_type)
                    
                    if entity_type:
                        where_conditions.append("al.entity_type = %s")
                        params.append(entity_type)
                    
                    if user_id:
                        where_conditions.append("al.user_id = %s")
                        params.append(int(user_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"""
                        SELECT COUNT(*) as total 
                        FROM action_logs al 
                        {where_clause}
                    """
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем логи
                    query = f"""
                        SELECT al.id, al.user_id, al.action_type, al.entity_type, al.entity_id,
                               al.description, al.ip_address, al.created_at,
                               au.fio as user_name, au.phone_e164 as user_phone
                        FROM action_logs al
                        LEFT JOIN app_user au ON al.user_id = au.user_id
                        {where_clause}
                        ORDER BY al.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    logs = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": logs,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": (total + limit - 1) // limit
                        }
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_log(self, request: Request) -> Response:
        """GET /api/logs/{log_id} - Получить лог по ID"""
        try:
            log_id = int(request.match_info['log_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT al.id, al.user_id, al.action_type, al.entity_type, al.entity_id,
                               al.description, al.ip_address, al.user_agent, al.created_at,
                               au.fio as user_name, au.phone_e164 as user_phone
                        FROM action_logs al
                        LEFT JOIN app_user au ON al.user_id = au.user_id
                        WHERE al.id = %s
                    """, (log_id,))
                    
                    log = await cur.fetchone()
                    
                    if not log:
                        return web.json_response({
                            "success": False,
                            "error": "Лог не найден"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": log
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID лога"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def create_log(self, request: Request) -> Response:
        """POST /api/logs - Создать лог"""
        try:
            data = await request.json()
            required_fields = ['action_type', 'description']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_action_types = ['login', 'logout', 'user_approve', 'user_reject', 'user_create', 
                                'user_update', 'user_delete', 'station_create', 'station_update', 
                                'station_delete', 'powerbank_create', 'powerbank_update', 
                                'powerbank_delete', 'group_create', 'group_update', 'group_delete', 
                                'order_create', 'order_update', 'order_delete', 'system_error', 'api_call',
                                'restart_command_sent', 'restart_response_received', 'restart_command_error']
            
            if data['action_type'] not in valid_action_types:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый тип действия. Допустимые значения: {', '.join(valid_action_types)}"
                }, status=400)
            
            valid_entity_types = ['user', 'station', 'powerbank', 'group', 'order', 'system']
            if 'entity_type' in data and data['entity_type'] not in valid_entity_types:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый тип сущности. Допустимые значения: {', '.join(valid_entity_types)}"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Получаем IP адрес из заголовков
                    ip_address = request.headers.get('X-Forwarded-For', 
                                                   request.headers.get('X-Real-IP', 
                                                                     request.remote))
                    user_agent = request.headers.get('User-Agent', '')
                    
                    await cur.execute("""
                        INSERT INTO action_logs (user_id, action_type, entity_type, entity_id, 
                                               description, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data.get('user_id'),
                        data['action_type'],
                        data.get('entity_type'),
                        data.get('entity_id'),
                        data['description'],
                        ip_address,
                        user_agent
                    ))
                    
                    log_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": log_id},
                        "message": "Лог создан"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_logs_stats(self, request: Request) -> Response:
        """GET /api/logs/stats - Получить статистику логов"""
        try:
            days = int(request.query.get('days', 7))
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Статистика по типам действий
                    await cur.execute("""
                        SELECT action_type, COUNT(*) as count
                        FROM action_logs 
                        WHERE created_at >= %s
                        GROUP BY action_type
                        ORDER BY count DESC
                    """, (datetime.now() - timedelta(days=days),))
                    action_stats = await cur.fetchall()
                    
                    # Статистика по дням
                    await cur.execute("""
                        SELECT DATE(created_at) as date, COUNT(*) as count
                        FROM action_logs 
                        WHERE created_at >= %s
                        GROUP BY DATE(created_at)
                        ORDER BY date DESC
                    """, (datetime.now() - timedelta(days=days),))
                    daily_stats = await cur.fetchall()
                    
                    # Статистика по пользователям
                    await cur.execute("""
                        SELECT au.fio as user_name, au.phone_e164 as user_phone, COUNT(*) as count
                        FROM action_logs al
                        LEFT JOIN app_user au ON al.user_id = au.user_id
                        WHERE al.created_at >= %s AND al.user_id IS NOT NULL
                        GROUP BY al.user_id, au.fio, au.phone_e164
                        ORDER BY count DESC
                        LIMIT 10
                    """, (datetime.now() - timedelta(days=days),))
                    user_stats = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": {
                            "action_stats": action_stats,
                            "daily_stats": daily_stats,
                            "user_stats": user_stats
                        }
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def clean_old_logs(self, request: Request) -> Response:
        """POST /api/logs/clean - Очистить старые логи"""
        try:
            data = await request.json() if request.content_type == 'application/json' else {}
            days = data.get('days', 90)  # По умолчанию удаляем логи старше 90 дней
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        DELETE FROM action_logs 
                        WHERE created_at < %s
                    """, (datetime.now() - timedelta(days=days),))
                    
                    deleted_count = cur.rowcount
                    
                    return web.json_response({
                        "success": True,
                        "data": {"deleted_count": deleted_count},
                        "message": f"Удалено {deleted_count} старых логов"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для логов CRUD"""
        app.router.add_get('/api/logs', self.get_logs)
        app.router.add_get('/api/logs/{log_id}', self.get_log)
        app.router.add_post('/api/logs', self.create_log)
        app.router.add_get('/api/logs/stats', self.get_logs_stats)
        app.router.add_post('/api/logs/clean', self.clean_old_logs)
