"""
CRUD API для управления powerbank
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime
from utils.json_utils import serialize_for_json
from utils.time_utils import get_moscow_time
from api.base_api import BaseAPI


class PowerbankCRUD(BaseAPI):
    """CRUD endpoints для powerbank"""
    
    def __init__(self, db_pool):
        super().__init__(db_pool)
    
    async def create_powerbank(self, request: Request) -> Response:
        """POST /api/powerbanks - Создать powerbank"""
        try:
            data = await request.json()
            required_fields = ['serial_number']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['active', 'user_reported_broken', 'system_error', 'written_off', 'unknown']
            valid_write_off_reasons = ['none', 'broken', 'lost', 'other']
            
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            if 'write_off_reason' in data and data['write_off_reason'] not in valid_write_off_reasons:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимая причина списания. Допустимые значения: {', '.join(valid_write_off_reasons)}"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем уникальность serial_number
                    await cur.execute("SELECT id FROM powerbank WHERE serial_number = %s", (data['serial_number'],))
                    if await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Аккумулятор с таким серийным номером уже существует"
                        }, status=400)
                    
                    # Создаем powerbank со статусом 'unknown' по умолчанию
                    await cur.execute("""
                        INSERT INTO powerbank (org_unit_id, serial_number, soh, status, write_off_reason)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        data.get('org_unit_id'),
                        data['serial_number'],
                        data.get('soh', 100),
                        data.get('status', 'unknown'),
                        data.get('write_off_reason', 'none')
                    ))
                    
                    powerbank_id = cur.lastrowid
                    
                    return web.json_response({
                        "success": True,
                        "data": {"id": powerbank_id},
                        "message": "Аккумулятор создан"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_powerbanks(self, request: Request) -> Response:
        """GET /api/powerbanks - Получить список powerbanks"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            org_unit_id = request.query.get('org_unit_id')
            
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
                    
                    # КРИТИЧНО: Фильтр удаленных записей (только основная таблица!)
                    self.add_is_deleted_filter(where_conditions, ['p'], show_deleted)
                    
                    if status:
                        where_conditions.append("p.status = %s")
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
                            where_conditions.append(f"p.org_unit_id IN ({placeholders})")
                            params.extend(accessible_org_units)
                    elif org_unit_id:
                        # Если service_admin указал конкретный org_unit_id
                        where_conditions.append("p.org_unit_id = %s")
                        params.append(int(org_unit_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM powerbank p {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем powerbanks
                    query = f"""
                        SELECT p.id, p.org_unit_id, p.serial_number, p.soh, 
                               p.status, p.write_off_reason, p.created_at, p.power_er,
                               ou.name as org_unit_name,
                               pe.type_error as error_type
                        FROM powerbank p
                        LEFT JOIN org_unit ou ON p.org_unit_id = ou.org_unit_id
                        LEFT JOIN powerbank_error pe ON p.power_er = pe.id_er
                        {where_clause}
                        ORDER BY p.created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    powerbanks = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": powerbanks,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": (total + limit - 1) // limit
                        }
                    }))
                    
        except Exception as e:
            import traceback
            from utils.centralized_logger import get_logger
            logger = get_logger('powerbank_crud')
            logger.error(f"ERROR in get_powerbanks: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_powerbank(self, request: Request) -> Response:
        """GET /api/powerbanks/{powerbank_id} - Получить аккумулятор по ID"""
        try:
            powerbank_id = int(request.match_info['powerbank_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT p.id, p.org_unit_id, p.serial_number, p.soh, 
                               p.status, p.write_off_reason, p.created_at, p.power_er,
                               ou.name as org_unit_name,
                               pe.type_error as error_type
                        FROM powerbank p
                        LEFT JOIN org_unit ou ON p.org_unit_id = ou.org_unit_id
                        LEFT JOIN powerbank_error pe ON p.power_er = pe.id_er
                        WHERE p.id = %s
                    """, (powerbank_id,))
                    
                    powerbank = await cur.fetchone()
                    if not powerbank:
                        return web.json_response({
                            "success": False,
                            "error": "Аккумулятор не найден"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": powerbank
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID аккумулятора"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def update_powerbank(self, request: Request) -> Response:
        """PUT /api/powerbanks/{powerbank_id} - Обновить аккумулятор"""
        try:
            powerbank_id = int(request.match_info['powerbank_id'])
            data = await request.json()
            
            # Поля для обновления
            update_fields = []
            params = []
            
            # Валидация enum значений
            valid_statuses = ['active', 'user_reported_broken', 'system_error', 'written_off', 'unknown']
            valid_write_off_reasons = ['none', 'broken', 'lost', 'other']
            
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            if 'write_off_reason' in data and data['write_off_reason'] not in valid_write_off_reasons:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимая причина списания. Допустимые значения: {', '.join(valid_write_off_reasons)}"
                }, status=400)
            
            allowed_fields = ['org_unit_id', 'serial_number', 'soh', 'status', 'write_off_reason']
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not update_fields:
                return web.json_response({
                    "success": False,
                    "error": "Нет полей для обновления"
                }, status=400)
            
            params.append(powerbank_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование powerbank
                    await cur.execute("SELECT id FROM powerbank WHERE id = %s", (powerbank_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Аккумулятор не найден"
                        }, status=404)
                    
                    # Обновляем
                    query = f"UPDATE powerbank SET {', '.join(update_fields)} WHERE id = %s"
                    await cur.execute(query, params)
                    
                    return web.json_response({
                        "success": True,
                        "message": "Аккумулятор обновлен"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID аккумулятора"
            }, status=400)
        except Exception as e:
            # Логируем детали ошибки
            try:
                from utils.centralized_logger import get_logger
                logger = get_logger('powerbank_crud')
                logger.error(f"Ошибка обновления powerbank {powerbank_id}: {str(e)}", exc_info=True)
            except:
                pass
            
            return web.json_response({
                "success": False,
                "error": f"Ошибка обновления powerbank: {str(e)}"
            }, status=500)
    
    async def delete_powerbank(self, request: Request) -> Response:
        """
        DELETE /api/powerbanks/{powerbank_id} - Мягкое удаление powerbank
        
        При удалении повербанка также меняется статус на 'unknown'
        """
        try:
            # Проверка авторизации
            auth_ok, error_response = self.check_auth(request)
            if not auth_ok:
                return error_response
            
            user = self.get_user_from_request(request)
            
            # Парсинг ID
            powerbank_id, error_response = self.parse_int_param(
                request.match_info['powerbank_id'], 'powerbank_id'
            )
            if error_response:
                return error_response
            
            # Проверка существования
            exists = await self.entity_exists('powerbank', 'id', powerbank_id)
            if not exists:
                return self.error_response("Powerbank не найден", 404)
            
            # Мягкое удаление
            success, message = await self.soft_delete_entity(
                'powerbank', powerbank_id, user.get('user_id')
            )
            
            if success:
                return self.success_response(message=message)
            else:
                return self.error_response(message, 404)
                    
        except Exception as e:
            return self.error_response(f"Ошибка при удалении: {str(e)}")
    
    async def approve_powerbank(self, request: Request) -> Response:
        """PUT /api/powerbanks/{powerbank_id}/approve - Одобрить аккумулятор"""
        try:
            powerbank_id = int(request.match_info['powerbank_id'])
            data = await request.json()
            
            if 'org_unit_id' not in data:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует обязательное поле: org_unit_id"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование powerbank
                    await cur.execute("SELECT id, serial_number, status, org_unit_id FROM powerbank WHERE id = %s", (powerbank_id,))
                    powerbank = await cur.fetchone()
                    if not powerbank:
                        return web.json_response({
                            "success": False,
                            "error": "Аккумулятор не найден"
                        }, status=404)
                    
                    # Проверяем, что powerbank имеет статус 'unknown'
                    if powerbank['status'] != 'unknown':
                        return web.json_response({
                            "success": False,
                            "error": "Можно одобрить только аккумулятор со статусом 'unknown'"
                        }, status=400)
                    
                    # Проверяем существование группы
                    await cur.execute("SELECT org_unit_id FROM org_unit WHERE org_unit_id = %s", (data['org_unit_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Группа/подгруппа не найдена"
                        }, status=400)
                    
                    # Проверяем, находится ли powerbank в станции и совместимость групп
                    await cur.execute("""
                        SELECT sp.station_id, sp.slot_number, s.org_unit_id as station_org_unit_id, s.box_id
                        FROM station_powerbank sp
                        INNER JOIN station s ON sp.station_id = s.station_id
                        WHERE sp.powerbank_id = %s
                    """, (powerbank_id,))
                    station_info = await cur.fetchone()
                    
                    # Проверяем совместимость групп, если powerbank в станции
                    if station_info and station_info['station_org_unit_id'] != data['org_unit_id']:
                        from utils.org_unit_utils import is_powerbank_compatible
                        compatible = await is_powerbank_compatible(
                            self.db_pool, data['org_unit_id'], station_info['station_org_unit_id']
                        )
                        
                        if not compatible:
                            return web.json_response({
                                "success": False,
                                "error": f"Аккумулятор нельзя одобрить в группу {data['org_unit_id']}, так как он находится в станции {station_info['box_id']} группы {station_info['station_org_unit_id']} и группы несовместимы. Сначала извлеките аккумулятор из станции."
                            }, status=400)
                    
                    # Обновляем статус на 'active' и назначаем группу
                    await cur.execute("""
                        UPDATE powerbank 
                        SET status = 'active', org_unit_id = %s, updated_at = %s
                        WHERE id = %s
                    """, (data['org_unit_id'], get_moscow_time(), powerbank_id))
                    
                    # Обновляем station_powerbank если powerbank находится в станции
                    if station_info:
                        await cur.execute("""
                            UPDATE station_powerbank 
                            SET last_update = %s
                            WHERE powerbank_id = %s AND station_id = %s
                        """, (get_moscow_time(), powerbank_id, station_info['station_id']))
                        
                        # Логируем одобрение аккумулятора в станции
                        from utils.centralized_logger import get_logger
                        logger = get_logger('powerbank_crud')
                        logger.info(f"Аккумулятор {powerbank['serial_number']} одобрен и активирован в группе {data['org_unit_id']}, находится в станции {station_info['box_id']}, слот {station_info['slot_number']}")
                    
                    return web.json_response({
                        "success": True,
                        "message": "Аккумулятор успешно одобрен и активирован",
                        "powerbank_id": powerbank_id,
                        "serial_number": powerbank['serial_number'],
                        "new_org_unit_id": data['org_unit_id'],
                        "in_station": station_info is not None,
                        "station_info": {
                            "station_id": station_info['station_id'],
                            "box_id": station_info['box_id'],
                            "slot_number": station_info['slot_number']
                        } if station_info else None
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID аккумулятора"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def reset_powerbank_error(self, request: Request) -> Response:
        """POST /api/powerbanks/{powerbank_id}/reset-error - Сбросить ошибку повербанка"""
        try:
            powerbank_id = int(request.match_info['powerbank_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование powerbank
                    await cur.execute("SELECT id, serial_number, status, power_er FROM powerbank WHERE id = %s", (powerbank_id,))
                    powerbank = await cur.fetchone()
                    if not powerbank:
                        return web.json_response({
                            "success": False,
                            "error": "Аккумулятор не найден"
                        }, status=404)
                    
                    # Сбрасываем ошибку и меняем статус на active
                    await cur.execute("""
                        UPDATE powerbank 
                        SET power_er = NULL, status = 'active'
                        WHERE id = %s
                    """, (powerbank_id,))
                    
                    # Логируем сброс ошибки
                    from utils.centralized_logger import get_logger
                    logger = get_logger('powerbank_crud')
                    logger.info(f"Ошибка аккумулятора {powerbank['serial_number']} (ID: {powerbank_id}) сброшена, статус изменен на 'active'")
                    
                    return web.json_response({
                        "success": True,
                        "message": "Ошибка повербанка успешно сброшена",
                        "powerbank_id": powerbank_id,
                        "serial_number": powerbank['serial_number']
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID аккумулятора"
            }, status=400)
        except Exception as e:
            # Логируем детали ошибки
            try:
                from utils.centralized_logger import get_logger
                logger = get_logger('powerbank_crud')
                logger.error(f"Ошибка сброса ошибки powerbank {powerbank_id}: {str(e)}", exc_info=True)
            except:
                pass
            
            return web.json_response({
                "success": False,
                "error": f"Ошибка сброса ошибки powerbank: {str(e)}"
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты для powerbank CRUD"""
        app.router.add_post('/api/powerbanks', self.create_powerbank)
        app.router.add_get('/api/powerbanks', self.get_powerbanks)
        app.router.add_get('/api/powerbanks/{powerbank_id}', self.get_powerbank)
        app.router.add_put('/api/powerbanks/{powerbank_id}', self.update_powerbank)
        app.router.add_put('/api/powerbanks/{powerbank_id}/approve', self.approve_powerbank)
        app.router.add_post('/api/powerbanks/{powerbank_id}/reset-error', self.reset_powerbank_error)
        app.router.add_delete('/api/powerbanks/{powerbank_id}', self.delete_powerbank)
