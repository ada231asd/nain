"""
CRUD API endpoints для всех таблиц базы данных
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime
from utils.json_utils import serialize_for_json


class CRUDEndpoints:
    """CRUD endpoints для всех таблиц БД"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # ==================== APP_USER CRUD ====================
    
    async def create_user(self, request: Request) -> Response:
        """POST /api/users - Создать пользователя"""
        try:
            data = await request.json()
            required_fields = ['fio', 'phone_e164', 'email', 'role', 'статус', 'password']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if data['статус'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус пользователя. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            valid_roles = ['user', 'subgroup_admin', 'group_admin', 'service_admin']
            if data['role'] not in valid_roles:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимая роль пользователя. Допустимые значения: {', '.join(valid_roles)}"
                }, status=400)
            
            # Валидация parent_org_unit_id
            parent_org_unit_id = data.get('parent_org_unit_id', '')
            if parent_org_unit_id and parent_org_unit_id != '':
                try:
                    parent_org_unit_id = int(parent_org_unit_id)
                except ValueError:
                    return web.json_response({
                        "success": False,
                        "error": "parent_org_unit_id должен быть числом или пустой строкой"
                    }, status=400)
            else:
                parent_org_unit_id = None
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование пользователя
                    await cur.execute(
                        "SELECT user_id FROM app_user WHERE phone_e164 = %s OR email = %s",
                        (data['phone_e164'], data['email'])
                    )
                    if await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь с таким телефоном или email уже существует"
                        }, status=400)
                    
                    # Хешируем пароль
                    import bcrypt
                    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Создаем пользователя
                    await cur.execute("""
                        INSERT INTO app_user (phone_e164, email, password_hash, fio, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        data['phone_e164'],
                        data['email'],
                        password_hash,
                        data['fio'],
                        data['статус']
                    ))
                    
                    user_id = cur.lastrowid
                    
                    # Создаем роль пользователя
                    await cur.execute("""
                        INSERT INTO user_role (user_id, role, org_unit_id)
                        VALUES (%s, %s, %s)
                    """, (user_id, data['role'], parent_org_unit_id))
                    
                    await conn.commit()
                    
                    return web.json_response({
                        "success": True,
                        "data": {
                            "user_id": user_id,
                            "fio": data['fio'],
                            "phone_e164": data['phone_e164'],
                            "email": data['email'],
                            "role": data['role'],
                            "parent_org_unit_id": parent_org_unit_id,
                            "статус": data['статус']
                        },
                        "message": "Пользователь создан"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_users(self, request: Request) -> Response:
        """GET /api/users - Получить список пользователей"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_clause = ""
                    params = []
                    
                    if status:
                        where_clause = "WHERE status = %s"
                        params.append(status)
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM app_user {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем пользователей с ролями и лимитами
                    query = f"""
                        SELECT 
                            au.user_id, 
                            au.phone_e164, 
                            au.email, 
                            au.fio, 
                            au.created_at, 
                            au.last_login_at,
                            COALESCE(ur.role, 'user') as role,
                            ur.org_unit_id as parent_org_unit_id,
                            au.powerbank_limit as individual_limit,
                            ou.default_powerbank_limit as group_default_limit,
                            ou.name as group_name
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
                        LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                        {where_clause.replace('status', 'au.status') if where_clause else ''}
                        ORDER BY au.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    users = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": users,
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
    
    async def get_user(self, request: Request) -> Response:
        """GET /api/users/{user_id} - Получить пользователя по ID"""
        try:
            user_id = int(request.match_info['user_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT 
                            au.user_id, 
                            au.phone_e164, 
                            au.email, 
                            au.fio, 
                            au.created_at, 
                            au.last_login_at,
                            COALESCE(ur.role, 'user') as role,
                            ur.org_unit_id as parent_org_unit_id,
                            au.powerbank_limit as individual_limit,
                            ou.default_powerbank_limit as group_default_limit,
                            ou.name as group_name
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
                        LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                        WHERE au.user_id = %s
                    """, (user_id,))
                    
                    user = await cur.fetchone()
                    if not user:
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": user
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID пользователя"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def update_user(self, request: Request) -> Response:
        """PUT /api/users/{user_id} - Обновить пользователя"""
        try:
            user_id = int(request.match_info['user_id'])
            data = await request.json()
            
            # Валидация обязательных полей
            required_fields = ['fio', 'phone_e164', 'email', 'role', 'статус']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if data['статус'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус пользователя. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            valid_roles = ['user', 'subgroup_admin', 'group_admin', 'service_admin']
            if data['role'] not in valid_roles:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимая роль пользователя. Допустимые значения: {', '.join(valid_roles)}"
                }, status=400)
            
            # Валидация parent_org_unit_id
            parent_org_unit_id = data.get('parent_org_unit_id', '')
            if parent_org_unit_id and parent_org_unit_id != '':
                try:
                    parent_org_unit_id = int(parent_org_unit_id)
                except ValueError:
                    return web.json_response({
                        "success": False,
                        "error": "parent_org_unit_id должен быть числом или пустой строкой"
                    }, status=400)
            else:
                parent_org_unit_id = None
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование пользователя
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (user_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=404)
                    
                    # Проверяем уникальность email и phone_e164
                    await cur.execute(
                        "SELECT user_id FROM app_user WHERE (email = %s OR phone_e164 = %s) AND user_id != %s",
                        (data['email'], data['phone_e164'], user_id)
                    )
                    if await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь с таким email или телефоном уже существует"
                        }, status=400)
                    
                    # Если обновляется пароль, хешируем его
                    password_hash = None
                    if 'password' in data and data['password']:
                        import bcrypt
                        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Обновляем основную таблицу пользователя
                    update_fields = []
                    params = []
                    
                    # Обновляем основные поля
                    update_fields.append("fio = %s")
                    params.append(data['fio'])
                    
                    update_fields.append("phone_e164 = %s")
                    params.append(data['phone_e164'])
                    
                    update_fields.append("email = %s")
                    params.append(data['email'])
                    
                    update_fields.append("status = %s")
                    params.append(data['статус'])
                    
                    # Добавляем поддержку обновления лимита повербанков
                    if 'individual_limit' in data or 'powerbank_limit' in data:
                        limit_value = data.get('individual_limit', data.get('powerbank_limit'))
                        if limit_value is not None and limit_value != '':
                            try:
                                limit_value = int(limit_value)
                                if limit_value < 0:
                                    return web.json_response({
                                        "success": False,
                                        "error": "Лимит повербанков не может быть отрицательным"
                                    }, status=400)
                            except (ValueError, TypeError):
                                return web.json_response({
                                    "success": False,
                                    "error": "Лимит повербанков должен быть числом"
                                }, status=400)
                        else:
                            limit_value = None
                        
                        update_fields.append("powerbank_limit = %s")
                        params.append(limit_value)
                    
                    if password_hash:
                        update_fields.append("password_hash = %s")
                        params.append(password_hash)
                    
                    params.append(user_id)
                    
                    # Обновляем пользователя
                    query = f"UPDATE app_user SET {', '.join(update_fields)} WHERE user_id = %s"
                    await cur.execute(query, params)
                    
                    # Обновляем или создаем роль пользователя
                    await cur.execute("SELECT id FROM user_role WHERE user_id = %s", (user_id,))
                    existing_role = await cur.fetchone()
                    
                    if existing_role:
                        # Обновляем существующую роль
                        await cur.execute("""
                            UPDATE user_role 
                            SET role = %s, org_unit_id = %s 
                            WHERE user_id = %s
                        """, (data['role'], parent_org_unit_id, user_id))
                    else:
                        # Создаем новую роль
                        await cur.execute("""
                            INSERT INTO user_role (user_id, role, org_unit_id)
                            VALUES (%s, %s, %s)
                        """, (user_id, data['role'], parent_org_unit_id))
                    
                    await conn.commit()

                    # Получаем актуальный индивидуальный лимит после обновления
                    await cur.execute("SELECT powerbank_limit FROM app_user WHERE user_id = %s", (user_id,))
                    limit_row = await cur.fetchone()
                    individual_limit_value = limit_row['powerbank_limit'] if limit_row else None
                    
                    return web.json_response({
                        "success": True,
                        "message": "Пользователь успешно обновлен",
                        "data": {
                            "user_id": user_id,
                            "fio": data['fio'],
                            "phone_e164": data['phone_e164'],
                            "email": data['email'],
                            "role": data['role'],
                            "parent_org_unit_id": parent_org_unit_id,
                            "individual_limit": individual_limit_value
                        }
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID пользователя"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_user(self, request: Request) -> Response:
        """DELETE /api/users/{user_id} - Удалить пользователя"""
        try:
            user_id = int(request.match_info['user_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (user_id,))
                    user = await cur.fetchone()
                    if not user:
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=404)
                    
                    
                    # Проверяем связанные записи
                    await cur.execute("SELECT COUNT(*) as count FROM orders WHERE user_id = %s", (user_id,))
                    orders_count = (await cur.fetchone())['count']
                    
                    await cur.execute("SELECT COUNT(*) as count FROM user_favorites WHERE user_id = %s", (user_id,))
                    favorites_count = (await cur.fetchone())['count']
                    
                    await cur.execute("SELECT COUNT(*) as count FROM user_role WHERE user_id = %s", (user_id,))
                    roles_count = (await cur.fetchone())['count']
                    
                    # Удаляем
                    await cur.execute("DELETE FROM app_user WHERE user_id = %s", (user_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Пользователь удален"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID пользователя"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    # ==================== STATION CRUD ====================
    
    async def create_station(self, request: Request) -> Response:
        """POST /api/stations - Создать станцию"""
        try:
            data = await request.json()
            required_fields = ['box_id', 'slots_declared']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['active', 'inactive', 'pending']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус станции. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем уникальность box_id
                    await cur.execute("SELECT station_id FROM station WHERE box_id = %s", (data['box_id'],))
                    if await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция с таким box_id уже существует"
                        }, status=400)
                    
                    # Создаем станцию
                    await cur.execute("""
                        INSERT INTO station (org_unit_id, box_id, iccid, slots_declared, remain_num, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        data.get('org_unit_id'),
                        data['box_id'],
                        data.get('iccid'),
                        data['slots_declared'],
                        data.get('remain_num', 0),
                        data.get('status', 'pending')
                    ))
                    
                    station_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"station_id": station_id},
                        "message": "Станция создана"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_stations(self, request: Request) -> Response:
        """GET /api/stations - Получить список станций"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            org_unit_id = request.query.get('org_unit_id')
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    if status:
                        where_conditions.append("s.status = %s")
                        params.append(status)
                    
                    if org_unit_id:
                        where_conditions.append("s.org_unit_id = %s")
                        params.append(int(org_unit_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM station s {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем станции
                    query = f"""
                        SELECT s.station_id, s.org_unit_id, s.box_id, s.iccid, 
                               s.slots_declared, s.remain_num, s.last_seen, 
                               s.created_at, s.updated_at, s.status,
                               ou.name as org_unit_name
                        FROM station s
                        LEFT JOIN org_unit ou ON s.org_unit_id = ou.org_unit_id
                        {where_clause}
                        ORDER BY s.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    stations = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": stations,
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
    
    async def get_station(self, request: Request) -> Response:
        """GET /api/stations/{station_id} - Получить станцию по ID"""
        try:
            station_id = int(request.match_info['station_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT s.station_id, s.org_unit_id, s.box_id, s.iccid, 
                               s.slots_declared, s.remain_num, s.last_seen, 
                               s.created_at, s.updated_at, s.status,
                               ou.name as org_unit_name
                        FROM station s
                        LEFT JOIN org_unit ou ON s.org_unit_id = ou.org_unit_id
                        WHERE s.station_id = %s
                    """, (station_id,))
                    
                    station = await cur.fetchone()
                    if not station:
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": station
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def update_station(self, request: Request) -> Response:
        """PUT /api/stations/{station_id} - Обновить станцию"""
        try:
            station_id = int(request.match_info['station_id'])
            data = await request.json()
            
            # Поля для обновления
            update_fields = []
            params = []
            
            # Валидация enum значений
            valid_statuses = ['active', 'inactive', 'pending']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус станции. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            allowed_fields = ['org_unit_id', 'box_id', 'iccid', 'slots_declared', 'remain_num', 'status']
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not update_fields:
                return web.json_response({
                    "success": False,
                    "error": "Нет полей для обновления"
                }, status=400)
            
            params.append(station_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование станции
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (station_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=404)
                    
                    # Обновляем
                    query = f"UPDATE station SET {', '.join(update_fields)} WHERE station_id = %s"
                    await cur.execute(query, params)
                    
                    return web.json_response({
                        "success": True,
                        "message": "Станция обновлена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_station(self, request: Request) -> Response:
        """DELETE /api/stations/{station_id} - Удалить станцию"""
        try:
            station_id = int(request.match_info['station_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (station_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM station WHERE station_id = %s", (station_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Станция удалена"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID станции"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты CRUD API"""
        
        # APP_USER routes
        app.router.add_post('/api/users', self.create_user)
        app.router.add_get('/api/users', self.get_users)
        app.router.add_get('/api/users/{user_id}', self.get_user)
        app.router.add_put('/api/users/{user_id}', self.update_user)
        app.router.add_delete('/api/users/{user_id}', self.delete_user)
        
        # STATION routes
        app.router.add_post('/api/stations', self.create_station)
        app.router.add_get('/api/stations', self.get_stations)
        app.router.add_get('/api/stations/{station_id}', self.get_station)
        app.router.add_put('/api/stations/{station_id}', self.update_station)
        app.router.add_delete('/api/stations/{station_id}', self.delete_station)
