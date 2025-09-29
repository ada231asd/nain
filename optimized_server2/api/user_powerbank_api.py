"""
API для работы с повербанками обычными пользователями
"""
from aiohttp import web
from aiohttp.web import Application
import aiomysql

from utils.centralized_logger import get_logger
from models.user import User
from models.powerbank import Powerbank
from models.station import Station
from models.order import Order
from handlers.borrow_powerbank import BorrowPowerbankHandler
from api.simple_return_api import SimpleReturnAPI
from utils.auth_middleware import jwt_middleware

class UserPowerbankAPI:
    """API для работы с повербанками обычными пользователями"""

    def __init__(self, db_pool: aiomysql.Pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.borrow_handler = BorrowPowerbankHandler(db_pool, connection_manager)
        self.return_api = SimpleReturnAPI(db_pool, connection_manager)
        self.logger = get_logger('userpowerbankapi')

    @jwt_middleware
    async def get_available_powerbanks(self, request: web.Request):
        """
        Получить список доступных повербанков для выдачи
        GET /api/user/powerbanks/available
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил список доступных повербанков")

        try:
            # Получаем все активные повербанки
            powerbanks = await Powerbank.get_all_active(self.db_pool)
            
            available_powerbanks = []
            for powerbank in powerbanks:
                # Проверяем, не выдан ли уже повербанк
                active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                if not active_order:
                    available_powerbanks.append({
                        "powerbank_id": powerbank.powerbank_id,
                        "serial_number": powerbank.serial_number,
                        "soh": powerbank.soh,
                        "status": powerbank.status
                    })

            return web.json_response({
                "success": True,
                "available_powerbanks": available_powerbanks,
                "count": len(available_powerbanks)
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения доступных повербанков для пользователя {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)

    @jwt_middleware
    async def get_user_orders(self, request: web.Request):
        """
        Получить заказы текущего пользователя
        GET /api/user/orders
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил свои заказы")

        try:
            # Получаем все заказы пользователя
            orders = await Order.get_by_user_id(self.db_pool, user_id)
            
            orders_data = []
            for order in orders:
                # Получаем информацию о повербанке
                powerbank = await Powerbank.get_by_id(self.db_pool, order.powerbank_id)
                # Получаем информацию о станции
                station = await Station.get_by_id(self.db_pool, order.station_id)
                
                orders_data.append({
                    "order_id": order.order_id,
                    "powerbank": {
                        "powerbank_id": powerbank.powerbank_id if powerbank else None,
                        "serial_number": powerbank.serial_number if powerbank else "Неизвестно"
                    },
                    "station": {
                        "station_id": station.station_id if station else None,
                        "box_id": station.box_id if station else "Неизвестно"
                    },
                    "status": order.status,
                    "borrow_time": order.borrow_time.isoformat() if order.borrow_time else None,
                    "return_time": order.return_time.isoformat() if order.return_time else None
                })

            return web.json_response({
                "success": True,
                "orders": orders_data
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения заказов пользователя {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)

    @jwt_middleware
    async def borrow_powerbank(self, request: web.Request):
        """
        Взять повербанк в аренду
        POST /api/user/powerbanks/borrow
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил выдачу повербанка")

        try:
            data = await request.json()
            powerbank_id = data.get('powerbank_id')
            station_id = data.get('station_id')

            if not powerbank_id or not station_id:
                return web.json_response({
                    "error": "Не указаны powerbank_id или station_id"
                }, status=400)

            # Проверяем, что повербанк существует и доступен
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return web.json_response({
                    "error": "Повербанк не найден"
                }, status=404)

            # Проверяем, что повербанк не выдан
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if active_order:
                return web.json_response({
                    "error": "Повербанк уже выдан другому пользователю"
                }, status=400)

            # Проверяем, что станция существует и активна
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    "error": "Станция не найдена"
                }, status=404)

            if station.status != 'active':
                return web.json_response({
                    "error": "Станция неактивна"
                }, status=400)

            # Создаем заказ
            order = await Order.create(
                self.db_pool,
                user_id,
                powerbank_id,
                station_id
            )

            if not order:
                return web.json_response({
                    "error": "Не удалось создать заказ"
                }, status=500)

            # Отправляем команду выдачи на станцию
            borrow_result = await self.borrow_handler.send_borrow_request(
                station_id, 
                powerbank_id, 
                user_id
            )

            if not borrow_result["success"]:
                # Если команда не отправилась, отменяем заказ
                await Order.cancel(self.db_pool, order.order_id)
                return web.json_response({
                    "error": f"Ошибка отправки команды на станцию: {borrow_result['message']}"
                }, status=500)

            self.logger.info(f"Пользователь {user_id} успешно взял повербанк {powerbank_id} со станции {station_id}")

            return web.json_response({
                "success": True,
                "message": "Повербанк успешно выдан",
                "order_id": order.order_id,
                "powerbank_serial": powerbank.serial_number,
                "station_box_id": station.box_id
            })

        except Exception as e:
            self.logger.error(f"Ошибка выдачи повербанка пользователю {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)

    @jwt_middleware
    async def return_powerbank(self, request: web.Request):
        """
        Вернуть повербанк
        POST /api/user/powerbanks/return
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил возврат повербанка")

        try:
            data = await request.json()
            order_id = data.get('order_id')
            station_id = data.get('station_id')

            if not order_id or not station_id:
                return web.json_response({
                    "error": "Не указаны order_id или station_id"
                }, status=400)

            # Получаем заказ
            order = await Order.get_by_id(self.db_pool, order_id)
            if not order:
                return web.json_response({
                    "error": "Заказ не найден"
                }, status=404)

            # Проверяем, что заказ принадлежит пользователю
            if order.user_id != user_id:
                return web.json_response({
                    "error": "Заказ не принадлежит текущему пользователю"
                }, status=403)

            # Проверяем, что заказ активен
            if order.status != 'active':
                return web.json_response({
                    "error": "Заказ неактивен"
                }, status=400)

            # Проверяем, что станция существует и активна
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    "error": "Станция не найдена"
                }, status=404)

            if station.status != 'active':
                return web.json_response({
                    "error": "Станция неактивна"
                }, status=400)

            # Выполняем возврат повербанка
            return_result = await self.return_api.return_powerbank(
                station_id,
                user_id,
                order.powerbank_id
            )

            if not return_result["success"]:
                return web.json_response({
                    "error": return_result["error"]
                }, status=500)

            self.logger.info(f"Пользователь {user_id} успешно вернул повербанк {order.powerbank_id} на станцию {station_id}")

            return web.json_response({
                "success": True,
                "message": "Повербанк успешно возвращен",
                "order_id": order.order_id,
                "station_box_id": station.box_id
            })

        except Exception as e:
            self.logger.error(f"Ошибка возврата повербанка пользователем {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)

    @jwt_middleware
    async def get_stations(self, request: web.Request):
        """
        Получить список активных станций
        GET /api/user/stations
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил список станций")

        try:
            # Получаем только активные станции
            stations = await Station.get_all_active(self.db_pool)
            
            stations_data = []
            for station in stations:
                stations_data.append({
                    "station_id": station.station_id,
                    "box_id": station.box_id,
                    "slots_declared": station.slots_declared,
                    "remain_num": station.remain_num,
                    "status": station.status,
                    "last_seen": station.last_seen.isoformat() if station.last_seen else None
                })

            return web.json_response({
                "success": True,
                "stations": stations_data
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения станций для пользователя {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)

    @jwt_middleware
    async def get_user_profile(self, request: web.Request):
        """
        Получить профиль текущего пользователя
        GET /api/user/profile
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил свой профиль")

        try:
            user = await User.get_by_id(self.db_pool, user_id)
            if not user:
                return web.json_response({
                    "error": "Пользователь не найден"
                }, status=404)

            # Получаем статистику пользователя
            active_orders = await Order.get_active_by_user_id(self.db_pool, user_id)
            total_orders = await Order.get_count_by_user_id(self.db_pool, user_id)

            return web.json_response({
                "success": True,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                },
                "statistics": {
                    "active_orders": len(active_orders),
                    "total_orders": total_orders
                }
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения профиля пользователя {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)
    
    @jwt_middleware
    async def return_damage_powerbank(self, request: web.Request):
        """
        Возврат повербанка с поломкой
        POST /api/return-damage
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил возврат повербанка с поломкой")

        try:
            data = await request.json()
            station_id = data.get('station_id')
            description = data.get('description', '')

            if not station_id:
                return web.json_response({
                    "success": False,
                    "error": "Не указан ID станции"
                }, status=400)

            if not description:
                return web.json_response({
                    "success": False,
                    "error": "Не указано описание проблемы"
                }, status=400)

            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return web.json_response({
                    "success": False,
                    "error": "Станция не найдена"
                }, status=404)

            # Используем обработчик возврата с поломкой
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            result = await return_handler.start_damage_return_process(station_id, user_id, description)
            
            if result.get('success'):
                return web.json_response({
                    "success": True,
                    "message": result.get('message'),
                    "station_id": station_id,
                    "user_id": user_id
                })
            else:
                return web.json_response({
                    "success": False,
                    "error": result.get('message', 'Ошибка возврата с поломкой')
                }, status=400)

        except Exception as e:
            self.logger.error(f"Ошибка возврата повербанка с поломкой для пользователя {user_id}: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)