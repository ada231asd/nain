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
from api.base_api import BaseAPI


class CRUDEndpoints(BaseAPI):
    """CRUD endpoints для всех таблиц БД"""
    
    def __init__(self, db_pool):
        super().__init__(db_pool)
    
    # ==================== APP_USER CRUD ====================
    
    async def create_user(self, request: Request) -> Response:
        """POST /api/users - Создать пользователя"""
        try:
            data = await request.json()
            required_fields = ['fio', 'phone_e164', 'email', 'role', 'status', 'password']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if data['status'] not in valid_statuses:
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
                        data['status']
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
                            "status": data['status']
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
            
            # Получаем доступные org_unit для текущего администратора
            user = request.get('user')
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
                    self.add_is_deleted_filter(where_conditions, ['au'], show_deleted)
                    
                    if status:
                        where_conditions.append("au.status = %s")
                        params.append(status)
                    
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
                            where_conditions.append(f"ur.org_unit_id IN ({placeholders})")
                            params.extend(accessible_org_units)
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"""
                        SELECT COUNT(DISTINCT au.user_id) as total 
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
                        {where_clause}
                    """
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
                            au.status as status,
                            COALESCE(ur.role, 'user') as role,
                            ur.org_unit_id as parent_org_unit_id,
                            au.powerbank_limit as individual_limit,
                            ou.default_powerbank_limit as group_default_limit,
                            ou.name as group_name
                        FROM app_user au
                        LEFT JOIN user_role ur ON au.user_id = ur.user_id
                        LEFT JOIN org_unit ou ON ur.org_unit_id = ou.org_unit_id
                        {where_clause}
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
                            au.status as status,
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
            
            # Защита: сервис-админ не может менять свою собственную роль
            try:
                current_user = request.get('user') or {}
                current_user_id = current_user.get('user_id')
                current_user_role = current_user.get('role') or current_user.get('user_role')
                # Если в middleware не проброшена роль, пробуем получить её из БД
                if (current_user_role is None) and current_user_id:
                    async with self.db_pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cur:
                            await cur.execute("SELECT role FROM user_role WHERE user_id = %s", (current_user_id,))
                            row = await cur.fetchone()
                            if row:
                                current_user_role = row.get('role')
                if current_user_id and current_user_role == 'service_admin' and current_user_id == user_id and 'role' in data and data['role'] != 'service_admin':
                    return web.json_response({
                        "success": False,
                        "error": "Сервис-администратор не может изменять собственную роль"
                    }, status=403)
            except Exception:
                # Если определение роли текущего пользователя не удалось, не блокируем прочие изменения
                pass
            
            # Валидация обязательных полей
            required_fields = ['fio', 'phone_e164', 'email', 'role']
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['pending', 'active', 'blocked']
            if 'status' in data and data['status'] not in valid_statuses:
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
                    
                    # Обновляем статус только если он передан
                    if 'status' in data:
                        update_fields.append("status = %s")
                        params.append(data['status'])
                    
                    # Добавляем поддержку обновления лимита повербанков
                    if 'individual_limit' in data or 'powerbank_limit' in data:
                        limit_value = data.get('individual_limit', data.get('powerbank_limit'))
                        print(f"DEBUG: Получен лимит: {limit_value}, тип: {type(limit_value)}")
                        
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
                        
                        print(f"DEBUG: Устанавливаем лимит: {limit_value}")
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
        """DELETE /api/users/{user_id} - Мягкое удаление пользователя"""
        try:
            # Проверка авторизации
            auth_ok, error_response = self.check_auth(request)
            if not auth_ok:
                return error_response
            
            user = self.get_user_from_request(request)
            
            # Парсинг ID
            user_id, error_response = self.parse_int_param(request.match_info['user_id'], 'user_id')
            if error_response:
                return error_response
            
            # Проверка существования
            exists = await self.entity_exists('app_user', 'user_id', user_id)
            if not exists:
                return self.error_response("Пользователь не найден", 404)
            
            # Мягкое удаление
            success, message = await self.soft_delete_entity('user', user_id, user.get('user_id'))
            
            if success:
                return self.success_response(message=message)
            else:
                return self.error_response(message, 404)
                    
        except Exception as e:
            return self.error_response(f"Ошибка при удалении: {str(e)}")
    
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
            # Если запрашивается конкретный box_id, увеличиваем лимит до 1000 (точный поиск)
            box_id = request.query.get('box_id')
            default_limit = 1000 if box_id else 10
            
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', default_limit))
            status = request.query.get('status')
            org_unit_id = request.query.get('org_unit_id')
            
            offset = (page - 1) * limit
            
            # Получаем доступные org_unit для текущего администратора
            user = request.get('user')
            accessible_org_units = None
            user_role = None
            if user:
                from utils.org_unit_utils import get_admin_accessible_org_units
                from models.user_role import UserRole
                accessible_org_units = await get_admin_accessible_org_units(self.db_pool, user['user_id'])
                user_role = await UserRole.get_primary_role(self.db_pool, user['user_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем нужно ли показывать удаленные
                    show_deleted = await self.should_show_deleted(request)
                    
                    # Строим запрос
                    where_conditions = []
                    params = []
                    
                    # КРИТИЧНО: Фильтр удаленных записей (только основная таблица!)
                    self.add_is_deleted_filter(where_conditions, ['s'], show_deleted)
                    
                    if status:
                        where_conditions.append("s.status = %s")
                        params.append(status)
                    
                    if box_id:
                        where_conditions.append("s.box_id = %s")
                        params.append(box_id)
                    
                    # Применяем фильтрацию по org_unit на основе прав доступа
                    if accessible_org_units is not None:  # None = service_admin (без фильтра)
                        if len(accessible_org_units) == 0:
                            # Пустой список означает:
                            # 1. Обычного пользователя (role='user') - показываем все станции
                            # 2. Администратора без org_unit - показываем все станции
                            # Не применяем фильтрацию, пользователь может видеть все станции
                            pass
                        else:
                            # Фильтруем по доступным org_units (для group_admin/subgroup_admin с org_unit)
                            placeholders = ','.join(['%s'] * len(accessible_org_units))
                            where_conditions.append(f"s.org_unit_id IN ({placeholders})")
                            params.extend(accessible_org_units)
                    elif org_unit_id:
                        # Если service_admin указал конкретный org_unit_id
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
                    
                    # Добавляем информацию о портах для каждой станции
                    # ВАЖНО: Используем remain_num как источник правды
                    for station in stations:
                        total_slots = station['slots_declared'] or 0
                        free_slots = station['remain_num'] or 0
                        occupied_slots = total_slots - free_slots
                        
                        station['free_ports'] = free_slots      # Свободные слоты (можно вернуть)
                        station['total_ports'] = total_slots    # Всего слотов
                        station['occupied_ports'] = occupied_slots  # Занятые слоты (можно взять)
                    
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
                    
                    # Добавляем информацию о портах
                    # ВАЖНО: Используем remain_num как источник правды для свободных слотов
                    # occupied_ports = total - free (не используем COUNT из station_powerbank, т.к. данные могут быть неактуальными)
                    total_slots = station['slots_declared'] or 0
                    free_slots = station['remain_num'] or 0
                    occupied_slots = total_slots - free_slots
                    
                    station['free_ports'] = free_slots      # Свободные слоты (можно вернуть)
                    station['total_ports'] = total_slots    # Всего слотов
                    station['occupied_ports'] = occupied_slots  # Занятые слоты (можно взять)
                    
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
            
            allowed_fields = ['org_unit_id', 'box_id', 'nik', 'iccid', 'slots_declared', 'remain_num', 'status']
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
    
    async def update_station_nik(self, request: Request) -> Response:
        """PUT /api/stations/{station_id}/nik - Обновить никнейм станции"""
        try:
            station_id = int(request.match_info['station_id'])
            data = await request.json()
            
            if 'nik' not in data:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует поле nik"
                }, status=400)
            
            nik = data['nik']
            
            # Ограничение длины никнейма (например, 50 символов)
            if len(nik) > 50:
                return web.json_response({
                    "success": False,
                    "error": "Никнейм не может превышать 50 символов"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование станции
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (station_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=404)
                    
                    # Обновляем никнейм
                    await cur.execute("UPDATE station SET nik = %s WHERE station_id = %s", (nik, station_id))
                    await conn.commit()
                    
                    return web.json_response({
                        "success": True,
                        "message": "Никнейм станции обновлен",
                        "data": {
                            "station_id": station_id,
                            "nik": nik
                        }
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
        """DELETE /api/stations/{station_id} - Мягкое удаление станции"""
        try:
            # Проверка авторизации
            auth_ok, error_response = self.check_auth(request)
            if not auth_ok:
                return error_response
            
            user = self.get_user_from_request(request)
            
            # Парсинг ID
            station_id, error_response = self.parse_int_param(request.match_info['station_id'], 'station_id')
            if error_response:
                return error_response
            
            # Проверка существования
            exists = await self.entity_exists('station', 'station_id', station_id)
            if not exists:
                return self.error_response("Станция не найдена", 404)
            
            # Мягкое удаление
            success, message = await self.soft_delete_entity('station', station_id, user.get('user_id'))
            
            if success:
                return self.success_response(message=message)
            else:
                return self.error_response(message, 404)
                    
        except Exception as e:
            return self.error_response(f"Ошибка при удалении: {str(e)}")
    
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
        app.router.add_put('/api/stations/{station_id}/nik', self.update_station_nik)
        app.router.add_delete('/api/stations/{station_id}', self.delete_station)
