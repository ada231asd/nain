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
from api.base_api import BaseAPI


class OrdersCRUD(BaseAPI):
    """CRUD endpoints для orders"""
    
    def __init__(self, db_pool):
        super().__init__(db_pool)
        self.db_pool = db_pool
    
    async def create_order(self, request: Request) -> Response:
        """POST /api/orders - Создать заказ (монолитная структура)"""
        try:
            data = await request.json()
            required_fields = ['station_box_id', 'user_phone', 'user_fio', 'status']
            
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
                    # Проверяем, является ли это административным заказом
                    is_admin_order = data.get('is_admin_order', False)
                    admin_user_id = data.get('admin_user_id')
                    
                    # Создаем заказ с монолитными полями
                    await cur.execute("""
                        INSERT INTO orders (
                            station_box_id, user_phone, user_fio,
                            powerbank_serial, org_unit_name,
                            status, timestamp, completed_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                    """, (
                        data['station_box_id'],
                        data['user_phone'],
                        data['user_fio'],
                        data.get('powerbank_serial'),
                        data.get('org_unit_name'),
                        data['status'],
                        data['timestamp'] if data['status'] == 'return' else None
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
                            description=f"Административный заказ: {data['status']}"
                        )
                    
                    # Получаем созданный заказ
                    await cur.execute("""
                        SELECT * FROM orders WHERE id = %s
                    """, (order_id,))
                    
                    order_data = await cur.fetchone()
                    
                    return web.json_response({
                        "success": True,
                        "data": {
                            "id": order_id,
                            "order": order_data,
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
        """GET /api/orders - Получить список заказов (монолитная структура)"""
        try:
            page = int(request.query.get('page', 1))
            limit = int(request.query.get('limit', 10))
            status = request.query.get('status')
            user_phone = request.query.get('user_phone')
            station_box_id = request.query.get('station_box_id')
            
            offset = (page - 1) * limit
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем нужно ли показывать удаленные
                    show_deleted = await self.should_show_deleted(request)
                    
                    # Строим условия для фильтрации
                    where_conditions = []
                    params = []
                    
                    # КРИТИЧНО: Фильтр удаленных записей
                    if not show_deleted:
                        where_conditions.append("is_deleted = 0")
                    
                    if status:
                        where_conditions.append("status = %s")
                        params.append(status)
                    
                    if user_phone:
                        where_conditions.append("user_phone = %s")
                        params.append(user_phone)
                    
                    if station_box_id:
                        where_conditions.append("station_box_id = %s")
                        params.append(station_box_id)
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
                    # Получаем общее количество
                    count_query = f"SELECT COUNT(*) as total FROM orders {where_clause}"
                    await cur.execute(count_query, params)
                    total = (await cur.fetchone())['total']
                    
                    # Получаем заказы
                    query = f"""
                        SELECT * FROM orders
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
                        }
                    }))
                    
        except Exception as e:
            import traceback
            from utils.centralized_logger import get_logger
            logger = get_logger('orders_crud')
            logger.error(f"ERROR in get_orders: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def get_order(self, request: Request) -> Response:
        """GET /api/orders/{order_id} - Получить заказ по ID (монолитная структура)"""
        try:
            order_id = int(request.match_info['order_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Получаем заказ с монолитными полями (только не удаленные)
                    await cur.execute("""
                        SELECT * FROM orders WHERE id = %s AND is_deleted = 0
                    """, (order_id,))
                    
                    order = await cur.fetchone()
                    if not order:
                        return web.json_response({
                            "success": False,
                            "error": "Заказ не найден"
                        }, status=404)
                    
                    return web.json_response(serialize_for_json({
                        "success": True,
                        "data": order
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
            valid_statuses = ['borrow', 'return']
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
                    # Проверяем существование заказа (только не удаленные)
                    await cur.execute("SELECT id FROM orders WHERE id = %s AND is_deleted = 0", (order_id,))
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
        """DELETE /api/orders/{order_id} - Мягкое удаление заказа"""
        try:
            order_id = int(request.match_info['order_id'])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существование
                    await cur.execute("SELECT id FROM orders WHERE id = %s AND is_deleted = 0", (order_id,))
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Заказ не найден"
                        }, status=404)
                    
                    # Мягкое удаление
                    from datetime import datetime
                    await cur.execute(
                        "UPDATE orders SET is_deleted = 1, deleted_at = %s WHERE id = %s",
                        (datetime.now(), order_id)
                    )
                    await conn.commit()
                    
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
    
    def setup_routes(self, app):
        """Настраивает маршруты для orders CRUD"""
        app.router.add_post('/api/orders', self.create_order)
        app.router.add_get('/api/orders', self.get_orders)
        app.router.add_get('/api/orders/{order_id}', self.get_order)
        app.router.add_put('/api/orders/{order_id}', self.update_order)
        app.router.add_delete('/api/orders/{order_id}', self.delete_order)
