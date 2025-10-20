"""
CRUD API для управления orders
"""
from aiohttp import web
from aiohttp.web import Request, Response
import json
from typing import Dict, Any, List, Optional
import aiomysql
from datetime import datetime
from utils.json_utils import serialize_for_json


class OrdersCRUD:
    """CRUD endpoints для orders"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def create_order(self, request: Request) -> Response:
        """POST /api/orders - Создать заказ"""
        try:
            data = await request.json()
            required_fields = ['station_id', 'user_id', 'status']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response({
                        "success": False,
                        "error": f"Отсутствует обязательное поле: {field}"
                    }, status=400)
            
            # Валидация enum значений
            valid_statuses = ['borrow', 'return', 'force_eject']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус заказа. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование станции и пользователя
                    await cur.execute("SELECT station_id FROM station WHERE station_id = %s", (data['station_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Станция не найдена"
                        }, status=400)
                    
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = %s", (data['user_id'],))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Пользователь не найден"
                        }, status=400)
                    
                    # Если указан powerbank_id, проверяем его существование
                    if 'powerbank_id' in data and data['powerbank_id']:
                        await cur.execute("SELECT id FROM powerbank WHERE id = %s", (data['powerbank_id'],))
                        if not await cur.fetchone():
                            return web.json_response({
                                "success": False,
                                "error": "Повербанк не найден"
                            }, status=400)
                    
                    # Если указан org_unit_id, проверяем его существование
                    if 'org_unit_id' in data and data['org_unit_id']:
                        await cur.execute("SELECT org_unit_id FROM org_unit WHERE org_unit_id = %s", (data['org_unit_id'],))
                        if not await cur.fetchone():
                            return web.json_response({
                                "success": False,
                                "error": "Организационная единица не найдена"
                            }, status=400)
                    
                    # Проверяем, является ли это административным заказом
                    is_admin_order = data.get('is_admin_order', False)
                    admin_user_id = data.get('admin_user_id')
                    
                    # Создаем заказ
                    await cur.execute("""
                        INSERT INTO orders (station_id, user_id, powerbank_id, org_unit_id, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        data['station_id'],
                        data['user_id'],
                        data.get('powerbank_id'),
                        data.get('org_unit_id'),
                        data['status']
                    ))
                    
                    order_id = cur.lastrowid
                    
                    # Если это административный заказ, логируем действие
                    if is_admin_order and admin_user_id:
                        from models.action_log import ActionLog
                        await ActionLog.create(
                            self.db_pool,
                            user_id=admin_user_id,
                            action_type='order_create',
                            entity_type='order',
                            entity_id=order_id,
                            description=f"Административный заказ: {data['status']} повербанка"
                        )
                    
                    # Получаем расширенные данные созданного заказа
                    await cur.execute("""
                        SELECT * FROM v_orders_extended WHERE id = %s
                    """, (order_id,))
                    
                    order_data = await cur.fetchone()
                    
                    return web.json_response({
                        "success": True,
                        "data": {
                            "id": order_id,
                            "extended_data": order_data,
                            "is_admin_order": is_admin_order
                        },
                        "message": "Заказ создан успешно"
                    })
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_orders(self, request: Request) -> Response:
        """GET /api/orders - Получить список заказов"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            user_id = request.query.get('user_id')
            station_id = request.query.get('station_id')
            use_extended = request.query.get('extended', 'false').lower() == 'true'
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    if use_extended:
                        # Используем представление v_orders_extended для расширенных данных
                        where_conditions = []
                        params = []
                        
                        if status:
                            where_conditions.append("status = %s")
                            params.append(status)
                        
                        if user_id:
                            where_conditions.append("user_id = %s")
                            params.append(int(user_id))
                        
                        if station_id:
                            where_conditions.append("station_id = %s")
                            params.append(int(station_id))
                        
                        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                        
                        # Получаем общее количество из представления
                        count_query = f"SELECT COUNT(*) as total FROM v_orders_extended {where_clause}"
                        await cur.execute(count_query, params)
                        total = (await cur.fetchone())['total']
                        
                        # Получаем расширенные данные заказов
                        query = f"""
                            SELECT * FROM v_orders_extended
                            {where_clause}
                            ORDER BY timestamp DESC
                            LIMIT %s OFFSET %s
                        """
                        await cur.execute(query, params + [limit, offset])
                        orders = await cur.fetchall()
                    else:
                        # Используем стандартный запрос для базовых данных
                        where_conditions = []
                        params = []
                        
                        if status:
                            where_conditions.append("o.status = %s")
                            params.append(status)
                        
                        if user_id:
                            where_conditions.append("o.user_id = %s")
                            params.append(int(user_id))
                        
                        if station_id:
                            where_conditions.append("o.station_id = %s")
                            params.append(int(station_id))
                        
                        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                        
                        # Получаем общее количество
                        count_query = f"SELECT COUNT(*) as total FROM orders o {where_clause}"
                        await cur.execute(count_query, params)
                        total = (await cur.fetchone())['total']
                        
                        # Получаем заказы
                        query = f"""
                            SELECT o.id, o.station_id, o.user_id, o.powerbank_id, o.status, o.timestamp,
                                   o.completed_at,
                                   s.box_id as station_box_id,
                                   u.phone_e164 as user_phone, u.fio as user_fio,
                                   p.serial_number as powerbank_serial
                            FROM orders o
                            LEFT JOIN station s ON o.station_id = s.station_id
                            LEFT JOIN app_user u ON o.user_id = u.user_id
                            LEFT JOIN powerbank p ON o.powerbank_id = p.id
                            {where_clause}
                            ORDER BY o.timestamp DESC
                            LIMIT %s OFFSET %s
                        """
                        await cur.execute(query, params + [limit, offset])
                        orders = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": orders,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": (total + limit - 1) // limit
                        },
                        "extended": use_extended
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_order(self, request: Request) -> Response:
        """GET /api/orders/{order_id} - Получить заказ по ID"""
        try:
            order_id = int(request.match_info['order_id'])
            use_extended = request.query.get('extended', 'false').lower() == 'true'
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    if use_extended:
                        # Используем представление v_orders_extended для расширенных данных
                        await cur.execute("""
                            SELECT * FROM v_orders_extended
                            WHERE id = %s
                        """, (order_id,))
                    else:
                        # Используем стандартный запрос
                        await cur.execute("""
                            SELECT o.id, o.station_id, o.user_id, o.powerbank_id, o.status, o.timestamp,
                                   o.completed_at,
                                   s.box_id as station_box_id,
                                   u.phone_e164 as user_phone, u.fio as user_fio,
                                   p.serial_number as powerbank_serial
                            FROM orders o
                            LEFT JOIN station s ON o.station_id = s.station_id
                            LEFT JOIN app_user u ON o.user_id = u.user_id
                            LEFT JOIN powerbank p ON o.powerbank_id = p.id
                            WHERE o.id = %s
                        """, (order_id,))
                    
                    order = await cur.fetchone()
                    if not order:
                        return web.json_response({
                            "success": False,
                            "error": "Заказ не найден"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": order,
                        "extended": use_extended
                    }))
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID заказа"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def update_order(self, request: Request) -> Response:
        """PUT /api/orders/{order_id} - Обновить заказ"""
        try:
            order_id = int(request.match_info['order_id'])
            data = await request.json()
            
            # Поля для обновления
            update_fields = []
            params = []
            
            # Валидация enum значений
            valid_statuses = ['borrow', 'return', 'force_eject']
            if 'status' in data and data['status'] not in valid_statuses:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимый статус заказа. Допустимые значения: {', '.join(valid_statuses)}"
                }, status=400)
            
            allowed_fields = ['station_id', 'user_id', 'powerbank_id', 'status']
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not update_fields:
                return web.json_response({
                    "success": False,
                    "error": "Нет полей для обновления"
                }, status=400)
            
            params.append(order_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование заказа
                    await cur.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Заказ не найден"
                        }, status=404)
                    
                    # Обновляем
                    query = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = %s"
                    await cur.execute(query, params)
                    
                    return web.json_response({
                        "success": True,
                        "message": "Заказ обновлен"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID заказа"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_order(self, request: Request) -> Response:
        """DELETE /api/orders/{order_id} - Удалить заказ"""
        try:
            order_id = int(request.match_info['order_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Заказ не найден"
                        }, status=404)
                    
                    # Удаляем
                    await cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
                    
                    return web.json_response({
                        "success": True,
                        "message": "Заказ удален"
                    })
                    
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Неверный ID заказа"
            }, status=400)
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_extended_orders(self, request: Request) -> Response:
        """GET /api/orders/extended - Получить расширенные данные заказов"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            user_id = request.query.get('user_id')
            station_id = request.query.get('station_id')
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Строим условия для фильтрации
                    where_conditions = []
                    params = []
                    
                    if status:
                        where_conditions.append("status = %s")
                        params.append(status)
                    
                    if user_id:
                        where_conditions.append("user_id = %s")
                        params.append(int(user_id))
                    
                    if station_id:
                        where_conditions.append("station_id = %s")
                        params.append(int(station_id))
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM v_orders_extended {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем расширенные данные заказов
                    query = f"""
                        SELECT * FROM v_orders_extended
                        {where_clause}
                        ORDER BY timestamp DESC
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, params + [limit, offset])
                    orders = await cur.fetchall()
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": orders,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": (total + limit - 1) // limit
                        },
                        "extended": True
                    }))
                    
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)

    def setup_routes(self, app):
        """Настраивает маршруты для orders CRUD"""
        app.router.add_post('/api/orders', self.create_order)
        app.router.add_get('/api/orders', self.get_orders)
        app.router.add_get('/api/orders/extended', self.get_extended_orders)
        app.router.add_get('/api/orders/{order_id}', self.get_order)
        app.router.add_put('/api/orders/{order_id}', self.update_order)
        app.router.add_delete('/api/orders/{order_id}', self.delete_order)
