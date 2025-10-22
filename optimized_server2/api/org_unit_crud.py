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


class OrgUnitCRUD:
    """CRUD endpoints для org_unit"""
    
    def __init__(self, db_pool):
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
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Создаем организационную единицу
                    await cur.execute("""
                        INSERT INTO org_unit (parent_org_unit_id, unit_type, name, adress, logo_url, default_powerbank_limit, reminder_hours)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data.get('parent_org_unit_id'),
                        data['unit_type'],
                        data['name'],
                        data.get('adress'),
                        data.get('logo_url'),
                        data.get('default_powerbank_limit', 1),
                        data.get('reminder_hours', 24)
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
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    if unit_type:
                        where_conditions.append("ou.unit_type = %s")
                        params.append(unit_type)
                    
                    if parent_id:
                        where_conditions.append("ou.parent_org_unit_id = %s")
                        params.append(int(parent_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM org_unit ou {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем организационные единицы
                    query = f"""
                        SELECT ou.org_unit_id, ou.parent_org_unit_id, ou.unit_type, 
                               ou.name, ou.adress, ou.logo_url, ou.created_at,
                               ou.default_powerbank_limit, ou.reminder_hours,
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
                               ou.default_powerbank_limit, ou.reminder_hours,
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
            
            allowed_fields = ['parent_org_unit_id', 'unit_type', 'name', 'adress', 'logo_url', 'default_powerbank_limit', 'reminder_hours']
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
