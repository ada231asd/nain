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
            required_fields = ['phone_e164', 'email', 'password']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
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
                    
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус пользователя. Допустимые значения: {', '.join(valid_statuses)}"
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
                data.get('fio'),
                data.get('status', 'pending')
            ))
            
            user_id = cur.lastrowid
            
            return web.json_response({
                "success": True,
                "data": {"user_id": user_id},
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
                    
                    # Получаем пользователей с ролями
                    query = f"""
                        SELECT 
                            au.user_id, 
                            au.phone_e164, 
                            au.email, 
                            au.fio, 
                            au.status, 
                            au.created_at, 
                            au.last_login_at,
                            COALESCE(ur.role, 'user') as role
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
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
                            au.status, 
                            au.created_at, 
                            au.last_login_at,
                            COALESCE(ur.role, 'user') as role
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
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
            
            # Поля для обновления
            update_fields = []
            params = []
            
            allowed_fields = ['phone_e164', 'email', 'fio', 'status', 'org_unit_id']
            
            # Если обновляется пароль, хешируем его
            if 'password' in data:
                import bcrypt
                data['password_hash'] = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                allowed_fields.append('password_hash')
                del data['password']
            
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус пользователя. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not update_fields:
                return web.json_response({
                    "success": False,
                    "error": "Нет полей для обновления"
                }, status=400)
            
            params.append(user_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование пользователя
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (user_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=404)
                    
                    # Обновляем
                    query = f"UPDATE app_user SET {', '.join(update_fields)} WHERE user_id = %s"
                    await cur.execute(query, params)
                    
                    return web.json_response({
                        "success": True,
                        "message": "Пользователь обновлен"
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
            print(f"🗑️ CRUDEndpoints: Удаляем пользователя {user_id}")
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (user_id,))
                    user = await cur.fetchone()
                    if not user:
                        print(f"❌ CRUDEndpoints: Пользователь {user_id} не найден")
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=404)
                    
                    print(f"✅ CRUDEndpoints: Пользователь {user_id} найден, начинаем удаление")
                    
                    # Проверяем связанные записи
                    await cur.execute("SELECT COUNT(*) as count FROM orders WHERE user_id = %s", (user_id,))
                    orders_count = (await cur.fetchone())['count']
                    print(f"📊 CRUDEndpoints: Связанных заказов: {orders_count}")
                    
                    await cur.execute("SELECT COUNT(*) as count FROM user_favorites WHERE user_id = %s", (user_id,))
                    favorites_count = (await cur.fetchone())['count']
                    print(f"📊 CRUDEndpoints: Связанных избранных: {favorites_count}")
                    
                    await cur.execute("SELECT COUNT(*) as count FROM user_role WHERE user_id = %s", (user_id,))
                    roles_count = (await cur.fetchone())['count']
                    print(f"📊 CRUDEndpoints: Связанных ролей: {roles_count}")
                    
                    # Удаляем
                    print(f"🗑️ CRUDEndpoints: Выполняем DELETE FROM app_user WHERE user_id = {user_id}")
                    await cur.execute("DELETE FROM app_user WHERE user_id = %s", (user_id,))
                    
                    print(f"✅ CRUDEndpoints: Пользователь {user_id} успешно удален")
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
