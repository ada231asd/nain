"""
CRUD API для остальных сущностей: user_role, user_favorites, station_powerbank, station_secret_key
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime
from utils.json_utils import serialize_for_json


class OtherEntitiesCRUD:
    """CRUD endpoints для остальных сущностей"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # ==================== USER_ROLE CRUD ====================
    
    async def create_user_role(self, request: Request) -> Response:
        """POST /api/user-roles - Создать роль пользователя"""
        try:
            data = await request.json()
            required_fields = ['user_id', 'role']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_roles = ['user', 'subgroup_admin', 'group_admin', 'service_admin']
            if 'role' in data and data['role'] not in valid_roles:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимая роль пользователя. Допустимые значения: {', '.join(valid_roles)}"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование пользователя
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (data['user_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=400)
                    
                    # Создаем роль пользователя
                    await cur.execute("""
                        INSERT INTO user_role (user_id, org_unit_id, role)
                        VALUES (%s, %s, %s)
                    """, (
                        data['user_id'],
                        data.get('org_unit_id'),
                        data['role']
                    ))
                    
                    role_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": role_id},
                        "message": "Роль пользователя создана"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_user_roles(self, request: Request) -> Response:
        """GET /api/user-roles - Получить список ролей пользователей"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            user_id = request.query.get('user_id')
            role = request.query.get('role')
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    if user_id:
                        where_conditions.append("ur.user_id = %s")
                        params.append(int(user_id))
                    
                    if role:
                        where_conditions.append("ur.role = %s")
                        params.append(role)
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM user_role ur {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем роли пользователей
                    query = f"""
                        SELECT ur.id, ur.user_id, ur.org_unit_id, ur.role, ur.created_at,
                               u.phone_e164 as user_phone, u.fio as user_fio,
                               ou.name as org_unit_name
                        FROM user_role ur
                        LEFT JOIN app_user u ON ur.user_id = u.user_id
                        LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                        {where_clause}
                        ORDER BY ur.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    user_roles = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": user_roles,
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
    
    async def delete_user_role(self, request: Request) -> Response:
        """DELETE /api/user-roles/{role_id} - Удалить роль пользователя"""
        try:
            role_id = int(request.match_info['role_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM user_role WHERE id = %s", (role_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Роль пользователя не найдена"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM user_role WHERE id = %s", (role_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Роль пользователя удалена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID роли"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    # ==================== USER_FAVORITES CRUD ====================
    
    async def create_user_favorite(self, request: Request) -> Response:
        """POST /api/user-favorites - Добавить станцию в избранное"""
        try:
            data = await request.json()
            required_fields = ['user_id', 'station_id']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование пользователя и станции
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (data['user_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=400)
                    
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (data['station_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=400)
                    
                    # Проверяем, не добавлена ли уже станция в избранное
                    await cur.execute("""
                        SELECT id FROM user_favorites WHERE user_id = %s AND station_id = %s
                    """, (data['user_id'], data['station_id']))
                    if await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция уже в избранном"
                        }, status=400)
                    
                    # Добавляем в избранное
                    await cur.execute("""
                        INSERT INTO user_favorites (user_id, station_id)
                        VALUES (%s, %s)
                    """, (data['user_id'], data['station_id']))
                    
                    favorite_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": favorite_id},
                        "message": "Станция добавлена в избранное"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_user_favorites(self, request: Request) -> Response:
        """GET /api/user-favorites - Получить избранные станции пользователя"""
        try:
            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    "success": False,
                    "error": "Не указан user_id"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT uf.id, uf.user_id, uf.station_id, uf.created_at,
                               s.box_id as station_box_id, s.status as station_status,
                               u.phone_e164 as user_phone
                        FROM user_favorites uf
                        LEFT JOIN station s ON uf.station_id = s.station_id
                        LEFT JOIN app_user u ON uf.user_id = u.user_id
                        WHERE uf.user_id = %s
                        ORDER BY uf.created_at DESC
                    """, (int(user_id),))
                    
                    favorites = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": favorites
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_user_favorite(self, request: Request) -> Response:
        """DELETE /api/user-favorites/{favorite_id} - Удалить из избранного"""
        try:
            favorite_id = int(request.match_info['favorite_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM user_favorites WHERE id = %s", (favorite_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Запись в избранном не найдена"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM user_favorites WHERE id = %s", (favorite_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Станция удалена из избранного"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID записи"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    # ==================== STATION_POWERBANK CRUD ====================
    
    async def create_station_powerbank(self, request: Request) -> Response:
        """POST /api/station-powerbanks - Создать связь станция-powerbank"""
        try:
            data = await request.json()
            required_fields = ['station_id', 'powerbank_id', 'slot_number']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование станции и powerbank
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (data['station_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=400)
                    
                    await cur.execute("SELECT id FROM powerbank WHERE id = %s", (data['powerbank_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Powerbank не найден"
                        }, status=400)
                    
                    # Создаем связь
                    await cur.execute("""
                        INSERT INTO station_powerbank (station_id, powerbank_id, slot_number, level, voltage, temperature)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        data['station_id'],
                        data['powerbank_id'],
                        data['slot_number'],
                        data.get('level'),
                        data.get('voltage'),
                        data.get('temperature')
                    ))
                    
                    sp_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": sp_id},
                        "message": "Связь станция-powerbank создана"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_station_powerbanks(self, request: Request) -> Response:
        """GET /api/station-powerbanks - Получить связи станция-powerbank"""
        try:
            station_id = request.query.get('station_id')
            powerbank_id = request.query.get('powerbank_id')
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    if station_id:
                        where_conditions.append("sp.station_id = %s")
                        params.append(int(station_id))
                    
                    if powerbank_id:
                        where_conditions.append("sp.powerbank_id = %s")
                        params.append(int(powerbank_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    await cur.execute(f"""
                        SELECT sp.id, sp.station_id, sp.powerbank_id, sp.slot_number,
                               sp.level, sp.voltage, sp.temperature, sp.last_update,
                               s.box_id as station_box_id,
                               p.serial_number as powerbank_serial
                        FROM station_powerbank sp
                        LEFT JOIN station s ON sp.station_id = s.station_id
                        LEFT JOIN powerbank p ON sp.powerbank_id = p.id
                        {where_clause}
                        ORDER BY sp.last_update DESC
                    """, params)
                    
                    station_powerbanks = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": station_powerbanks
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_station_powerbank(self, request: Request) -> Response:
        """DELETE /api/station-powerbanks/{sp_id} - Удалить связь станция-powerbank"""
        try:
            sp_id = int(request.match_info['sp_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM station_powerbank WHERE id = %s", (sp_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Связь не найдена"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM station_powerbank WHERE id = %s", (sp_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Связь удалена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID связи"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    # ==================== STATION_SECRET_KEY CRUD ====================
    
    async def create_station_secret_key(self, request: Request) -> Response:
        """POST /api/station-secret-keys - Создать секретный ключ станции"""
        try:
            data = await request.json()
            required_fields = ['station_id', 'key_value']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование станции
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (data['station_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=400)
                    
                    # Создаем секретный ключ
                    await cur.execute("""
                        INSERT INTO station_secret_key (station_id, key_value)
                        VALUES (%s, %s)
                    """, (data['station_id'], data['key_value']))
                    
                    key_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": key_id},
                        "message": "Секретный ключ создан"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_station_secret_keys(self, request: Request) -> Response:
        """GET /api/station-secret-keys - Получить секретные ключи станций"""
        try:
            station_id = request.query.get('station_id')
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    if station_id:
                        await cur.execute("""
                            SELECT ssk.id, ssk.station_id, ssk.key_value,
                                   s.box_id as station_box_id
                            FROM station_secret_key ssk
                            LEFT JOIN station s ON ssk.station_id = s.station_id
                            WHERE ssk.station_id = %s
                        """, (int(station_id),))
                    else:
                        await cur.execute("""
                            SELECT ssk.id, ssk.station_id, ssk.key_value,
                                   s.box_id as station_box_id
                            FROM station_secret_key ssk
                            LEFT JOIN station s ON ssk.station_id = s.station_id
                            ORDER BY ssk.station_id
                        """)
                    
                    secret_keys = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": secret_keys
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_station_secret_key(self, request: Request) -> Response:
        """DELETE /api/station-secret-keys/{key_id} - Удалить секретный ключ"""
        try:
            key_id = int(request.match_info['key_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM station_secret_key WHERE id = %s", (key_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Секретный ключ не найден"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM station_secret_key WHERE id = %s", (key_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Секретный ключ удален"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID ключа"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_station_secret_key_by_station(self, request: Request) -> Response:
        """DELETE /api/station-secret-keys - Удалить секретный ключ по station_id"""
        try:
            data = await request.json()
            station_id = data.get('station_id')
            
            if not station_id:
                return web.json_response({
                    "success": False,
                    "error": "station_id обязателен"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM station_secret_key WHERE station_id = %s", (station_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Секретный ключ для станции не найден"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM station_secret_key WHERE station_id = %s", (station_id,))
                    await conn.commit()
            
            return web.json_response({
                "success": True,
                "message": "Секретный ключ станции удален"
            })
            
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для остальных сущностей"""
        
        # USER_ROLE routes
        app.router.add_post('/api/user-roles', self.create_user_role)
        app.router.add_get('/api/user-roles', self.get_user_roles)
        app.router.add_delete('/api/user-roles/{role_id}', self.delete_user_role)
        
        # USER_FAVORITES routes
        app.router.add_post('/api/user-favorites', self.create_user_favorite)
        app.router.add_get('/api/user-favorites', self.get_user_favorites)
        app.router.add_delete('/api/user-favorites/{favorite_id}', self.delete_user_favorite)
        
        # STATION_POWERBANK routes
        app.router.add_post('/api/station-powerbanks', self.create_station_powerbank)
        app.router.add_get('/api/station-powerbanks', self.get_station_powerbanks)
        app.router.add_delete('/api/station-powerbanks/{sp_id}', self.delete_station_powerbank)
        
        # STATION_SECRET_KEY routes
        app.router.add_post('/api/station-secret-keys', self.create_station_secret_key)
        app.router.add_get('/api/station-secret-keys', self.get_station_secret_keys)
        app.router.add_delete('/api/station-secret-keys/{key_id}', self.delete_station_secret_key)
        app.router.add_delete('/api/station-secret-keys', self.delete_station_secret_key_by_station)
