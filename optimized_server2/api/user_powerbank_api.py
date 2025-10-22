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
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил список доступных повербанков")

        try:
        # Получаем информацию о лимитах пользователя
            from utils.order_utils import get_user_limit_info
            limit_info = await get_user_limit_info(self.db_pool, user_id)
        
            user_limit = limit_info.get('effective_limit')
            current_borrowed = limit_info.get('active_count', 0)
            limit_type = limit_info.get('limit_type')
        
        # Обрабатываем случай неограниченного лимита (для админов)
            if user_limit is None and limit_type == 'role_exempt':
            # Админы могут брать неограниченное количество
                available_by_limit = float('inf')  # бесконечность
                user_limit_display = "unlimited"
            else:
            # Обычные пользователи с лимитом
                user_limit = user_limit or 0
                available_by_limit = max(0, user_limit - current_borrowed)
                user_limit_display = user_limit

        # Если лимит исчерпан (и не админ), возвращаем пустой список
            if available_by_limit <= 0 and limit_type != 'role_exempt':
                return json_ok({
                    "available_powerbanks": [],
                    "count": 0,
                    "user_limits": {
                        "max_limit": user_limit_display,
                        "current_borrowed": current_borrowed,
                        "available_by_limit": 0
                    },
                    "message": "Лимит повербанков исчерпан"
                })

        # Получаем все активные повербанки
            powerbanks = await Powerbank.get_all_active(self.db_pool)
        
            from utils.org_unit_utils import can_user_borrow_powerbank
        
            available_powerbanks = []
            for powerbank in powerbanks:
                # Если не админ и достигли лимита, прекращаем
                if limit_type != 'role_exempt' and len(available_powerbanks) >= available_by_limit:
                    break

                # Проверяем, не выдан ли уже повербанк
                active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                if not active_order:
                    # Проверяем права доступа
                    can_borrow, access_reason = await can_user_borrow_powerbank(
                        self.db_pool, user_id, powerbank.powerbank_id
                    )

                    if can_borrow:
                        available_powerbanks.append({
                            "powerbank_id": powerbank.powerbank_id,
                            "serial_number": powerbank.serial_number,
                            "soh": powerbank.soh,
                            "status": powerbank.status,
                            "access_reason": access_reason
                        })

            self.logger.info(f"Пользователь {user_id}: лимит={user_limit_display}, уже взято={current_borrowed}, доступно={len(available_powerbanks)}")

            return json_ok({
                "available_powerbanks": available_powerbanks,
                "count": len(available_powerbanks),
                "user_limits": {
                    "max_limit": user_limit_display,
                    "current_borrowed": current_borrowed,
                    "available_by_limit": available_by_limit if limit_type != 'role_exempt' else "unlimited"
                }
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения доступных повербанков для пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

    async def _get_user_available_powerbanks(self, user_id: int):
        """
        Вспомогательный метод для получения доступных повербанков пользователя
        Возвращает список словарей с информацией о доступных повербанках
        """
        try:
            # Получаем информацию о лимитах пользователя
            from utils.order_utils import get_user_limit_info
            limit_info = await get_user_limit_info(self.db_pool, user_id)
            
            user_limit = limit_info.get('effective_limit')
            current_borrowed = limit_info.get('active_count', 0)
            limit_type = limit_info.get('limit_type')
            
            # Обрабатываем случай неограниченного лимита (для админов)
            if user_limit is None and limit_type == 'role_exempt':
                # Админы могут брать неограниченное количество
                available_by_limit = float('inf')  # бесконечность
            else:
                # Обычные пользователи с лимитом
                user_limit = user_limit or 0
                available_by_limit = max(0, user_limit - current_borrowed)
            
            # Если лимит исчерпан (и не админ), возвращаем пустой список
            if available_by_limit <= 0 and limit_type != 'role_exempt':
                return []

            # Получаем все активные повербанки
            powerbanks = await Powerbank.get_all_active(self.db_pool)
            
            # Импортируем функцию проверки доступа
            from utils.org_unit_utils import can_user_borrow_powerbank
            
            available_powerbanks = []
            for powerbank in powerbanks:
                # Если не админ и достигли лимита, прекращаем
                if limit_type != 'role_exempt' and len(available_powerbanks) >= available_by_limit:
                    break

                # Проверяем, не выдан ли уже повербанк
                active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                if not active_order:
                    # Проверяем права доступа
                    can_borrow, access_reason = await can_user_borrow_powerbank(
                        self.db_pool, user_id, powerbank.powerbank_id
                    )

                    if can_borrow:
                        available_powerbanks.append({
                            "powerbank_id": powerbank.powerbank_id,
                            "serial_number": powerbank.serial_number,
                            "soh": powerbank.soh,
                            "status": powerbank.status,
                            "access_reason": access_reason
                        })

            return available_powerbanks

        except Exception as e:
            self.logger.error(f"Ошибка получения доступных повербанков для пользователя {user_id}: {e}", exc_info=True)
            return []

    @jwt_middleware
    async def get_user_orders(self, request: web.Request):
        """
        Получить заказы текущего пользователя с расширенными данными
        GET /api/user/orders
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил свои заказы")

        try:
            # Используем новый метод для получения расширенных данных
            from models.order import Order
            orders_data = await Order.get_extended_by_user_id(self.db_pool, user_id, limit=50, offset=0)
            
            return json_ok({
                "orders": orders_data
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения заказов пользователя {user_id}: {e}", exc_info=True)
            return json_fail(f"Внутренняя ошибка сервера: {e}", status=500)

    @jwt_middleware
    async def borrow_powerbank(self, request: web.Request):
        """
        Взять повербанк в аренду (сервер сам выбирает повербанк)
        POST /api/user/powerbanks/borrow
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил выдачу повербанка")

        try:
            data = await request.json()
            station_id = data.get('station_id')  

            if not station_id:
                return json_fail("Не указан station_id", status=400)

            # Получаем доступные повербанки для пользователя
            available_powerbanks = await self._get_user_available_powerbanks(user_id)
            
            if not available_powerbanks:
                return json_fail("Нет доступных повербанков для выдачи", status=400)

            # Фильтруем повербанки которые находятся в запрошенной станции
            from models.station_powerbank import StationPowerbank
            
            station_available_powerbanks = []
            for pb in available_powerbanks:
                # Проверяем что повербанк находится в этой станции
                station_pb = await StationPowerbank.get_by_powerbank_id(self.db_pool, pb['powerbank_id'])
                if station_pb and station_pb.station_id == station_id:
                    station_available_powerbanks.append(pb)
            
            if not station_available_powerbanks:
                return json_fail("В указанной станции нет доступных повербанков", status=400)

            # ВЫБИРАЕМ ПЕРВЫЙ ДОСТУПНЫЙ ПОВЕРБАНК ИЗ СТАНЦИИ
            selected_powerbank = station_available_powerbanks[0]
            powerbank_id = selected_powerbank['powerbank_id']
            
            self.logger.info(f"Автоматически выбран повербанк {powerbank_id} для пользователя {user_id}")

            # Проверяем права доступа пользователя к станции
            from utils.org_unit_utils import can_user_access_station, log_access_denied_event
            
            can_access_station, station_access_reason = await can_user_access_station(self.db_pool, user_id, station_id)
            if not can_access_station:
                await log_access_denied_event(self.db_pool, user_id, 'station', station_id, station_access_reason)
                return json_fail(station_access_reason, status=403)

            # Проверяем права доступа пользователя к повербанку
            from utils.org_unit_utils import can_user_borrow_powerbank
            
            can_borrow, access_reason = await can_user_borrow_powerbank(self.db_pool, user_id, powerbank_id)
            if not can_borrow:
                await log_access_denied_event(self.db_pool, user_id, 'powerbank', powerbank_id, access_reason)
                return json_fail(access_reason, status=403)

            # Проверяем, что повербанк существует
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return json_fail("Повербанк не найден", status=404)

            # Проверяем, что повербанк не выдан
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if active_order:
                return json_fail("Повербанк уже выдан другому пользователю", status=400)

            # Проверяем лимит повербанков пользователя
            from utils.order_utils import check_user_powerbank_limit, get_user_limit_info
            limit_ok, limit_message = await check_user_powerbank_limit(self.db_pool, user_id)
            limit_info = await get_user_limit_info(self.db_pool, user_id)
            if not limit_ok:
                return json_fail(limit_message, status=403, limit=limit_info)

            # Проверяем онлайн статус станции
            if self.connection_manager:
                connection = self.connection_manager.get_connection_by_station_id(station_id)
                if not connection:
                    return json_fail("Станция не подключена", status=503)
                
                # Проверяем последний heartbeat
                if connection.last_heartbeat:
                    from datetime import datetime
                    from utils.time_utils import get_moscow_time
                    time_since_heartbeat = (get_moscow_time() - connection.last_heartbeat).total_seconds()
                    if time_since_heartbeat > 30:
                        return json_fail(f"Станция офлайн (последний heartbeat {time_since_heartbeat:.0f} секунд назад)", status=503)
                else:
                    return json_fail("Станция не отправляла heartbeat", status=503)

            # Проверяем, что станция существует и активна
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            if station.status != 'active':
                return json_fail("Станция неактивна", status=400)

            # Создаем заказ со статусом 'pending'
            order = await Order.create_pending_order(
                self.db_pool,
                user_id,
                powerbank_id,
                station_id
            )

            if not order:
                return json_fail("Не удалось создать заказ", status=500)

            # Отправляем команду выдачи на станцию
            borrow_result = await self.borrow_handler.send_borrow_request_and_wait(
                station_id, 
                powerbank_id, 
                user_id,
                order.order_id
            )

            if borrow_result["success"]:
                # Станция подтвердила выдачу
                await Order.confirm_borrow(self.db_pool, order.order_id)
                
                self.logger.info(f"Пользователь {user_id} успешно взял повербанк {powerbank_id} со станции {station_id}")

                # Получаем обновленную информацию о лимитах
                updated_limit_info = await get_user_limit_info(self.db_pool, user_id)
                
                return json_ok({
                    "message": "Повербанк успешно выдан",
                    "order_id": order.order_id,
                    "powerbank_serial": powerbank.serial_number,
                    "station_box_id": station.box_id,
                    "user_limits": {
                        "max_limit": updated_limit_info.get('effective_limit'),
                        "current_borrowed": updated_limit_info.get('active_count', 0),
                        "available_by_limit": max(0, (updated_limit_info.get('effective_limit') or 0) - updated_limit_info.get('active_count', 0))
                    }
                }, limit=updated_limit_info)
            else:
                # Станция отклонила выдачу
                await Order.delete(self.db_pool, order.order_id)
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
    async def get_available_slots_with_limits(self, request: web.Request):
        """
        Получить доступные слоты станций с учетом лимитов пользователя
        GET /api/user/stations/availability
        """
        user_id = request['user']['user_id']
        self.logger.info(f"Пользователь {user_id} запросил доступные слоты станций")

        try:
            # Получаем информацию о лимитах пользователя
            from utils.order_utils import get_user_limit_info
            limit_info = await get_user_limit_info(self.db_pool, user_id)
            
            self.logger.info(f"Информация о лимитах пользователя {user_id}: {limit_info}")
            
            # Определяем текущий лимит пользователя
            user_limit = limit_info.get('effective_limit')
            current_borrowed = limit_info.get('active_count', 0)
            limit_type = limit_info.get('limit_type')
            
            # Для админов (role_exempt) лимиты не применяются
            if limit_type == 'role_exempt':
                self.logger.info(f"Пользователь {user_id} - администратор, лимиты не применяются")
                # Для админов не ограничиваем количество
                user_limit_for_response = "unlimited"
                available_by_limit_for_response = "unlimited"
                # Для расчетов используем очень большое число
                available_by_limit = 999999
            else:
                # Для обычных пользователей вычисляем доступное количество
                user_limit = user_limit or 0
                available_by_limit = max(0, user_limit - current_borrowed)
                user_limit_for_response = user_limit
                available_by_limit_for_response = available_by_limit
            
            # Получаем только активные станции
            stations = await Station.get_all_active(self.db_pool)
            
            # Импортируем функцию проверки доступа к станции
            from utils.org_unit_utils import can_user_access_station
            
            stations_data = []
            total_available_slots = 0
            
            for station in stations:
                # Проверяем права доступа пользователя к станции
                can_access, access_reason = await can_user_access_station(self.db_pool, user_id, station.station_id)
                
                if can_access:
                    # Получаем повербанки в станции
                    from models.station_powerbank import StationPowerbank
                    station_powerbanks = await StationPowerbank.get_station_powerbanks(self.db_pool, station.station_id)
                    
                    # Подсчитываем доступные повербанки (не выданные)
                    available_count = 0
                    for sp in station_powerbanks:
                        # Проверяем, не выдан ли повербанк
                        active_order = await Order.get_active_by_powerbank_id(self.db_pool, sp.powerbank_id)
                        if not active_order:
                            available_count += 1
                    
                    # Ограничиваем количество доступных слотов лимитом пользователя
                    user_available_slots = min(available_count, available_by_limit)
                    total_available_slots += user_available_slots
                    
                    stations_data.append({
                        "station_id": station.station_id,
                        "box_id": station.box_id,
                        "slots_declared": station.slots_declared,
                        "remain_num": station.remain_num,
                        "available_powerbanks": available_count,
                        "user_available_slots": user_available_slots,
                        "status": station.status,
                        "last_seen": station.last_seen.isoformat() if station.last_seen else None,
                        "access_reason": access_reason
                    })

            return json_ok({
                "stations": stations_data,
                "total_available_slots": total_available_slots,
                "user_limits": {
                    "max_limit": user_limit_for_response,
                    "current_borrowed": current_borrowed,
                    "available_by_limit": available_by_limit_for_response
                }
            })

        except Exception as e:
            self.logger.error(f"Ошибка получения доступных слотов для пользователя {user_id}: {e}", exc_info=True)
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
            error_type = data.get('error_type', 'other')

            if not station_id:
                return json_fail("Не указан ID станции", status=400)

            if not user_id:
                return json_fail("Не указан ID пользователя", status=400)


            self.logger.info(f"Пользователь {user_id} запросил возврат повербанка с поломкой: {error_type}")

            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return json_fail("Станция не найдена", status=404)

            # Используем обработчик возврата с поломкой
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            result = await return_handler.start_damage_return_process(station_id, user_id, error_type)
            
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
                self.logger.info(f" Получен error_type_id: {error_type_id}, тип: {type(error_type_id)}")
                error_type_id = int(error_type_id)
                if error_type_id <= 0:
                    return json_fail("ID типа ошибки должен быть положительным числом", status=400)
                self.logger.info(f" error_type_id после конвертации: {error_type_id}")
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
            
            # Получаем timeout из параметров запроса (по умолчанию 30 секунд)
            timeout_seconds = int(data.get('timeout_seconds', 30))
            
            result = await return_handler.handle_error_return_request(user_id, station_id, error_type_id, timeout_seconds)
            
            if result.get('success'):
                return json_ok({
                    "message": result.get('message'),
                    "station_id": result.get('station_id'),
                    "user_id": result.get('user_id'),
                    "error_type": result.get('error_type'),
                    "error_name": result.get('error_name')
                })
            else:
                return json_fail(result.get('error'), status=400)
                
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