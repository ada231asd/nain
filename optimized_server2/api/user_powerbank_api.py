"""
API для работы с повербанками обычными пользователями
"""
from aiohttp import web
from aiohttp.web import Application
import aiomysql

from utils.centralized_logger import get_logger
from utils.json_utils import json_ok, json_fail
from models.user import User
from models.powerbank import Powerbank
from models.station import Station
from models.order import Order
from handlers.borrow_powerbank import BorrowPowerbankHandler
from utils.auth_middleware import jwt_middleware

class UserPowerbankAPI:
    """API для работы с повербанками обычными пользователями"""

    def __init__(self, db_pool: aiomysql.Pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.borrow_handler = BorrowPowerbankHandler(db_pool, connection_manager)
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
            
            # Импортируем функцию проверки доступа
            from utils.org_unit_utils import can_user_borrow_powerbank
            
            available_powerbanks = []
            for powerbank in powerbanks:
                # Проверяем, не выдан ли уже повербанк
                active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                if not active_order:
                    # Проверяем права доступа пользователя к этому повербанку
                    can_borrow, access_reason = await can_user_borrow_powerbank(
                        self.db_pool, user_id, powerbank.powerbank_id
                    )
                    
                    if can_borrow:
                        available_powerbanks.append({
                            "powerbank_id": powerbank.powerbank_id,
                            "serial_number": powerbank.serial_number,
                            "soh": powerbank.soh,
                            "status": powerbank.status,
                            "access_reason": access_reason  # Добавляем причину доступа для информации
                        })

            return json_ok({
                "available_powerbanks": available_powerbanks,
                "count": len(available_powerbanks)
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения доступных повербанков для пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

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

            return json_ok({
                "orders": orders_data
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения заказов пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

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
                return json_fail("Не указаны powerbank_id или station_id", status=400)

            # Проверяем права доступа пользователя к повербанку
            from utils.org_unit_utils import can_user_borrow_powerbank, log_access_denied_event
            
            can_borrow, access_reason = await can_user_borrow_powerbank(self.db_pool, user_id, powerbank_id)
            if not can_borrow:
                # Логируем отказ в доступе
                await log_access_denied_event(self.db_pool, user_id, 'powerbank', powerbank_id, access_reason)
                return json_fail(access_reason, status=403)

            # Проверяем, что повербанк существует и доступен (дополнительная проверка)
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return json_fail("Повербанк не найден", status=404)

            # Проверяем, что повербанк не выдан
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if active_order:
                return json_fail("Повербанк уже выдан другому пользователю", status=400)

            # Проверяем лимит повербанков пользователя (индивидуальный или групповой по умолчанию)
            from utils.order_utils import check_user_powerbank_limit
            limit_ok, limit_message = await check_user_powerbank_limit(self.db_pool, user_id)
            from utils.order_utils import get_user_limit_info
            limit_info = await get_user_limit_info(self.db_pool, user_id)
            if not limit_ok:
                return json_fail(limit_message, status=403, limit=limit_info)

            # Проверяем онлайн статус станции
            from models.connection import ConnectionManager
            connection_manager = self.connection_manager
            if connection_manager:
                connection = connection_manager.get_connection_by_station_id(station_id)
                if not connection:
                    return json_fail("Станция не подключена", status=503)
                
                # Проверяем последний heartbeat (не более 30 секунд назад)
                if connection.last_heartbeat:
                    from datetime import datetime
                    from utils.time_utils import get_moscow_time
                    time_since_heartbeat = (get_moscow_time() - connection.last_heartbeat).total_seconds()
                    if time_since_heartbeat > 30:
                        return json_fail(f"Станция офлайн (последний heartbeat {time_since_heartbeat:.0f} секунд назад)", status=503)
                else:
                    return json_fail("Станция не отправляла heartbeat", status=503)
            
            # Проверяем права доступа пользователя к станции
            from utils.org_unit_utils import can_user_access_station
            
            can_access_station, station_access_reason = await can_user_access_station(self.db_pool, user_id, station_id)
            if not can_access_station:
                # Логируем отказ в доступе к станции
                await log_access_denied_event(self.db_pool, user_id, 'station', station_id, station_access_reason)
                return json_fail(station_access_reason, status=403)

            # Проверяем, что станция существует и активна (дополнительная проверка)
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            if station.status != 'active':
                return json_fail("Станция неактивна", status=400)

            # Создаем заказ со статусом 'pending' (ожидание ответа от станции)
            order = await Order.create_pending_order(
                self.db_pool,
                user_id,
                powerbank_id,
                station_id
            )

            if not order:
                return json_fail("Не удалось создать заказ", status=500)

            # Отправляем команду выдачи на станцию и ждем ответа
            borrow_result = await self.borrow_handler.send_borrow_request_and_wait(
                station_id, 
                powerbank_id, 
                user_id,
                order.order_id
            )

            if borrow_result["success"]:
                # Станция подтвердила выдачу - обновляем заказ на 'borrow'
                await Order.confirm_borrow(self.db_pool, order.order_id)
                
                self.logger.info(f"Пользователь {user_id} успешно взял повербанк {powerbank_id} со станции {station_id}")

                return json_ok({
                    "message": "Повербанк успешно выдан",
                    "order_id": order.order_id,
                    "powerbank_serial": powerbank.serial_number,
                    "station_box_id": station.box_id
                }, limit=limit_info)
            else:
                # Станция отклонила выдачу - отменяем заказ
                await Order.cancel(self.db_pool, order.order_id)
                return json_fail(f"Станция отклонила выдачу: {borrow_result['message']}", status=400)

        except Exception as e:
            self.logger.error(f"Ошибка выдачи повербанка пользователю {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

    @jwt_middleware
    async def return_powerbank(self, request: web.Request):
        """
        Ручной возврат повербанка (вариант 3)
        POST /api/user/powerbanks/return
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил ручной возврат повербанка")

        try:
            data = await request.json()
            order_id = data.get('order_id')
            station_id = data.get('station_id')

            if not order_id or not station_id:
                return json_fail("Не указаны order_id или station_id", status=400)

            # Получаем заказ
            order = await Order.get_by_id(self.db_pool, order_id)
            if not order:
                return json_fail("Заказ не найден", status=404)

            # Проверяем, что заказ принадлежит пользователю
            if order.user_id != user_id:
                return json_fail("Заказ не принадлежит текущему пользователю", status=403)

            # Проверяем, что заказ активен
            if order.status != 'borrow':
                return json_fail("Заказ неактивен или уже возвращен", status=400)

            # Проверяем, что станция существует и активна
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            if station.status != 'active':
                return json_fail("Станция неактивна", status=400)

            # Используем обработчик возврата для ручного возврата
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            result = await return_handler.start_manual_return_process(station_id, user_id, order_id)

            if result.get('success'):
                self.logger.info(f"Пользователь {user_id} успешно вернул повербанк {order.powerbank_id} на станцию {station_id}")
                return json_ok({
                    "message": result.get('message', 'Повербанк успешно возвращен'),
                    "order_id": order.order_id,
                    "station_box_id": station.box_id,
                    "powerbank_inserted": result.get('powerbank_inserted', False)
                })
            else:
                return json_fail(result.get('message', 'Ошибка возврата повербанка'), status=500)

        except Exception as e:
            self.logger.error(f"Ошибка возврата повербанка пользователем {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

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

            return json_ok({
                "stations": stations_data
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения станций для пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

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
                return json_fail("Пользователь не найден", status=404)

            # Получаем статистику пользователя
            active_orders = await Order.get_active_by_user_id(self.db_pool, user_id)
            total_orders = await Order.get_count_by_user_id(self.db_pool, user_id)

            return json_ok({
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
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)
    
    async def return_damage_powerbank(self, request: web.Request):
        """
        Возврат повербанка с поломкой
        POST /api/return-damage
        """
        try:
            data = await request.json()
            station_id = data.get('station_id')
            user_id = data.get('user_id')
            description = data.get('description', '')
            error_type = data.get('error_type', 'other')

            if not station_id:
                return json_fail("Не указан ID станции", status=400)

            if not user_id:
                return json_fail("Не указан ID пользователя", status=400)

            if not description:
                return json_fail("Не указано описание проблемы", status=400)

            # Проверяем допустимые типы ошибок
            valid_error_types = ['broken', 'lost', 'other']
            if error_type not in valid_error_types:
                return json_fail(f"Недопустимый тип ошибки. Допустимые значения: {', '.join(valid_error_types)}", status=400)

            self.logger.info(f"Пользователь {user_id} запросил возврат повербанка с поломкой: {error_type}")

            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            # Используем обработчик возврата с поломкой
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            result = await return_handler.start_damage_return_process(station_id, user_id, description, error_type)
            
            if result.get('success'):
                return json_ok({
                    "message": result.get('message'),
                    "station_id": station_id,
                    "user_id": user_id,
                    "error_type": error_type,
                    "powerbank_id": result.get('powerbank_id'),
                    "new_status": result.get('new_status'),
                    "write_off_reason": result.get('write_off_reason')
                })
            else:
                return json_fail(result.get('message', 'Ошибка возврата с поломкой'), status=400)

        except Exception as e:
            self.logger.error(f"Ошибка возврата повербанка с поломкой для пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)
    
    async def return_error_powerbank(self, request: web.Request):
        """
        Возврат повербанка с ошибкой (удерживает соединение до получения данных о вставке)
        POST /api/return-error
        """
        try:
            data = await request.json()
            station_id = data.get('station_id')
            user_id = data.get('user_id')
            error_type_id = data.get('error_type_id', 1)  # По умолчанию ID = 1

            if not station_id:
                return json_fail("Не указан ID станции", status=400)

            if not user_id:
                return json_fail("Не указан ID пользователя", status=400)

            # Валидируем ID типа ошибки
            try:
                error_type_id = int(error_type_id)
                if error_type_id <= 0:
                    return json_fail("ID типа ошибки должен быть положительным числом", status=400)
            except (ValueError, TypeError):
                return json_fail("Неверный формат ID типа ошибки", status=400)

            self.logger.info(f"Пользователь {user_id} запросил возврат повербанка с ошибкой: ID={error_type_id}")

            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            # Используем обработчик возврата с ошибкой
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            result = await return_handler.start_error_return_process(station_id, user_id, error_type_id)
            
            if result.get('success'):
                return json_ok({
                    "message": result.get('message'),
                    "station_id": station_id,
                    "user_id": user_id,
                    "error_type_id": error_type_id,
                    "error_description": result.get('error_description'),
                    "slot": result.get('slot'),
                    "terminal_id": result.get('terminal_id'),
                    "powerbank_id": result.get('powerbank_id'),
                    "order_id": result.get('order_id')
                })
            else:
                return json_fail(result.get('message'), status=400)
                
        except Exception as e:
            self.logger.error(f"Ошибка возврата с ошибкой: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)
    
    async def get_powerbank_error_types(self, request: web.Request):
        """
        Получение доступных типов ошибок повербанков
        GET /api/powerbank-error-types
        """
        try:
            from models.powerbank_error import PowerbankError
            
            error_types = await PowerbankError.get_all(self.db_pool)
            
            return json_ok({
                "error_types": [error.to_dict() for error in error_types]
            })
                
        except Exception as e:
            self.logger.error(f"Ошибка получения типов ошибок: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)