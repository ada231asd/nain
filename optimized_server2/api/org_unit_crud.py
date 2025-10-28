"""
CRUD API для управления org_unit
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime
from utils.json_utils import serialize_for_json
from api.base_api import BaseAPI


class OrgUnitCRUD(BaseAPI):
    """CRUD endpoints для org_unit"""
    
    def __init__(self, db_pool):
        super().__init__(db_pool)
        self.db_pool = db_pool
    
    async def create_org_unit(self, request: Request) -> Response:
        """POST /api/org-units - Создать организационную единицу"""
        try:
            data = await request.json()
            required_fields = ['unit_type', 'name']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_unit_types = ['group', 'subgroup']
            if 'unit_type' in data and data['unit_type'] not in valid_unit_types:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый тип организационной единицы. Допустимые значения: {', '.join(valid_unit_types)}"
                }, status=400)
            
            # Валидация: группа не должна иметь родительскую группу
            if data['unit_type'] == 'group' and data.get('parent_org_unit_id'):
                return web.json_response({
                    "success": False,
                    "error": "Группа не может иметь родительскую группу"
                }, status=400)
            
            # Валидация: подгруппа должна иметь родительскую группу
            if data['unit_type'] == 'subgroup' and not data.get('parent_org_unit_id'):
                return web.json_response({
                    "success": False,
                    "error": "Подгруппа должна иметь родительскую группу"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверка типа родительской группы
                    if data.get('parent_org_unit_id'):
                        await cur.execute("""
                            SELECT unit_type FROM org_unit WHERE org_unit_id = %s
                        """, (data['parent_org_unit_id'],))
                        parent_data = await cur.fetchone()
                        if not parent_data:
                            return web.json_response({
                                "success": False,
                                "error": "Родительская группа не найдена"
                            }, status=400)
                        if parent_data['unit_type'] != 'group':
                            return web.json_response({
                                "success": False,
                                "error": "Подгруппа может иметь родителем только группу"
                            }, status=400)
                    
                    # Создаем организационную единицу
                    await cur.execute("""
                        INSERT INTO org_unit (parent_org_unit_id, unit_type, name, adress, logo_url, default_powerbank_limit, reminder_hours, write_off_hours)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data.get('parent_org_unit_id') if data['unit_type'] == 'subgroup' else None,
                        data['unit_type'],
                        data['name'],
                        data.get('adress'),
                        data.get('logo_url'),
                        data.get('default_powerbank_limit', 1),
                        data.get('reminder_hours', 24),
                        data.get('write_off_hours', 48)
                    ))
                    
                    org_unit_id = cur.lastrowid
                    await conn.commit()
                    
                    return web.json_response({
                        "success": True,
                        "data": {"org_unit_id": org_unit_id},
                        "message": "Организационная единица создана"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_org_units(self, request: Request) -> Response:
        """GET /api/org-units - Получить список организационных единиц"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            unit_type = request.query.get('unit_type')
            parent_id = request.query.get('parent_id')
            
            offset = (page - 1) * limit
            
            # Получаем доступные org_unit для текущего администратора
            user = self.get_user_from_request(request)
            accessible_org_units = None
            if user:
                from utils.org_unit_utils import get_admin_accessible_org_units
                accessible_org_units = await get_admin_accessible_org_units(self.db_pool, user['user_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем нужно ли показывать удаленные
                    show_deleted = await self.should_show_deleted(request)
                    
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    # КРИТИЧНО: Фильтр удаленных записей
                    self.add_is_deleted_filter(where_conditions, ['ou'], show_deleted)
                    
                    if unit_type:
                        where_conditions.append("ou.unit_type = %s")
                        params.append(unit_type)
                    
                    if parent_id:
                        where_conditions.append("ou.parent_org_unit_id = %s")
                        params.append(int(parent_id))
                    
                    # Применяем фильтрацию по org_unit на основе прав доступа
                    if accessible_org_units is not None:  # None = service_admin (без фильтра)
                        if len(accessible_org_units) == 0:
                            # Нет доступных org_units - возвращаем пустой результат
                            return web.json_response(serialize_for_json({
                                "success": True,
                                "data": [],
                                "pagination": {
                                    "page": page,
                                    "limit": limit,
                                    "total": 0,
                                    "pages": 0
                                }
                            }))
                        else:
                            # Фильтруем по доступным org_units
                            placeholders = ','.join(['%s'] * len(accessible_org_units))
                            where_conditions.append(f"ou.org_unit_id IN ({placeholders})")
                            params.extend(accessible_org_units)
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM org_unit ou {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем организационные единицы
                    query = f"""
                        SELECT ou.org_unit_id, ou.parent_org_unit_id, ou.unit_type, 
                               ou.name, ou.adress, ou.logo_url, ou.created_at,
                               ou.default_powerbank_limit, ou.reminder_hours, ou.write_off_hours,
                               parent.name as parent_name
                        FROM org_unit ou
                        LEFT JOIN org_unit parent ON ou.parent_org_unit_id = parent.org_unit_id
                        {where_clause}
                        ORDER BY ou.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    org_units = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": org_units,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": (total + limit - 1) // limit
                        }
                    }))
                    
        except Exception as e:
            from utils.centralized_logger import log_error
            log_error(__name__, f"ERROR in get_org_units: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_org_unit(self, request: Request) -> Response:
        """GET /api/org-units/{org_unit_id} - Получить организационную единицу по ID"""
        try:
            org_unit_id = int(request.match_info['org_unit_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT ou.org_unit_id, ou.parent_org_unit_id, ou.unit_type, 
                               ou.name, ou.adress, ou.logo_url, ou.created_at,
                               ou.default_powerbank_limit, ou.reminder_hours, ou.write_off_hours,
                               parent.name as parent_name
                        FROM org_unit ou
                        LEFT JOIN org_unit parent ON ou.parent_org_unit_id = parent.org_unit_id
                        WHERE ou.org_unit_id = %s
                    """, (org_unit_id,))
                    
                    org_unit = await cur.fetchone()
                    if not org_unit:
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": org_unit
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID организационной единицы"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def update_org_unit(self, request: Request) -> Response:
        """PUT /api/org-units/{org_unit_id} - Обновить организационную единицу"""
        try:
            org_unit_id = int(request.match_info['org_unit_id'])
            data = await request.json()
            
            # Поля для обновления
            update_fields = []
            params = []
            
            # Валидация enum значений
            valid_unit_types = ['group', 'subgroup']
            if 'unit_type' in data and data['unit_type'] not in valid_unit_types:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый тип организационной единицы. Допустимые значения: {', '.join(valid_unit_types)}"
                }, status=400)
            
            # Проверяем текущий unit_type и новые данные
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Получаем текущий unit_type
                    await cur.execute("SELECT unit_type FROM org_unit WHERE org_unit_id = %s", (org_unit_id,))
                    current_unit = await cur.fetchone()
                    if not current_unit:
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
                    
                    current_unit_type = data.get('unit_type', current_unit['unit_type'])
                    new_parent_id = data.get('parent_org_unit_id')
                    
                    # Валидация: группа не должна иметь родительскую группу
                    if current_unit_type == 'group' and new_parent_id:
                        return web.json_response({
                            "success": False,
                            "error": "Группа не может иметь родительскую группу"
                        }, status=400)
                    
                    # Валидация: подгруппа должна иметь родительскую группу
                    if current_unit_type == 'subgroup' and new_parent_id is None and 'parent_org_unit_id' in data:
                        return web.json_response({
                            "success": False,
                            "error": "Подгруппа должна иметь родительскую группу"
                        }, status=400)
                    
                    # Проверка типа родительской группы
                    if new_parent_id and 'parent_org_unit_id' in data:
                        await cur.execute("""
                            SELECT unit_type FROM org_unit WHERE org_unit_id = %s
                        """, (new_parent_id,))
                        parent_data = await cur.fetchone()
                        if not parent_data:
                            return web.json_response({
                                "success": False,
                                "error": "Родительская группа не найдена"
                            }, status=400)
                        if parent_data['unit_type'] != 'group':
                            return web.json_response({
                                "success": False,
                                "error": "Подгруппа может иметь родителем только группу"
                            }, status=400)
            
            allowed_fields = ['parent_org_unit_id', 'unit_type', 'name', 'adress', 'logo_url', 'default_powerbank_limit', 'reminder_hours', 'write_off_hours']
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not update_fields:
                return web.json_response({
                    "success": False,
                    "error": "Нет полей для обновления"
                }, status=400)
            
            params.append(org_unit_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование организационной единицы
                    await cur.execute("SELECT org_unit_id FROM org_unit WHERE org_unit_id = %s", (org_unit_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
                    
                    # Обновляем
                    query = f"UPDATE org_unit SET {', '.join(update_fields)} WHERE org_unit_id = %s"
                    await cur.execute(query, params)
                    await conn.commit()
                    
                    return web.json_response({
                        "success": True,
                        "message": "Организационная единица обновлена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID организационной единицы"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_org_unit(self, request: Request) -> Response:
        """DELETE /api/org-units/{org_unit_id} - Удалить организационную единицу"""
        try:
            org_unit_id = int(request.match_info['org_unit_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT org_unit_id FROM org_unit WHERE org_unit_id = %s", (org_unit_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM org_unit WHERE org_unit_id = %s", (org_unit_id,))
                    await conn.commit()
                    
                    return web.json_response({
                        "success": True,
                        "message": "Организационная единица удалена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID организационной единицы"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для org_unit CRUD"""
        app.router.add_post('/api/org-units', self.create_org_unit)
        app.router.add_get('/api/org-units', self.get_org_units)
        app.router.add_get('/api/org-units/{org_unit_id}', self.get_org_unit)
        app.router.add_put('/api/org-units/{org_unit_id}', self.update_org_unit)
        app.router.add_delete('/api/org-units/{org_unit_id}', self.delete_org_unit)
