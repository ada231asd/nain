"""
Обработчик для возврата повербанков с ошибкой
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from models.powerbank_error import PowerbankError
from models.action_log import ActionLog
from utils.centralized_logger import get_logger
from utils.time_utils import get_moscow_time


class ReturnPowerbankHandler:
    """Обработчик для возврата повербанков с ошибкой"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('return_powerbank')
        if not hasattr(ReturnPowerbankHandler, '_pending_error_returns'):
            ReturnPowerbankHandler._pending_error_returns = {}
        self.pending_error_returns = ReturnPowerbankHandler._pending_error_returns
    
    async def _send_inventory_request_silently(self, station_id: int) -> None:
        """
        Отправляет запрос инвентаризации без логирования в фоновом режиме
        """
        try:
            from utils.packet_utils import build_query_inventory_request
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return
                
            # Проверяем writer более тщательно
            writer = getattr(connection, 'writer', None)
            if not writer or writer.is_closing():
                return
            
            secret_key = connection.secret_key
            if not secret_key:
                return
            
            # Строим и отправляем запрос инвентаризации
            inventory_request_packet = build_query_inventory_request(
                secret_key=secret_key,
                vsn=2,
                station_box_id=connection.box_id or f"station_{station_id}"
            )
            
            # Дополнительная проверка перед записью
            if not writer.is_closing():
                writer.write(inventory_request_packet)
                await writer.drain()
            
        except (ConnectionError, OSError, asyncio.CancelledError):
            # Игнорируем ошибки соединения (без логирования)
            pass
        except Exception:
            # Игнорируем остальные ошибки (без логирования)
            pass

    async def start_background_cleanup(self):
        """Запускает фоновую очистку просроченных запросов. Вызывать после старта event loop."""
        asyncio.create_task(self._cleanup_expired_requests())
    
    async def handle_error_return_request(self, user_id: int, station_id: int, error_type: int, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Обрабатывает запрос на возврат повербанка с ошибкой с Long Polling
        Ждет вставки повербанка в станцию до timeout_seconds секунд
        """
        try:
            # Проверяем, что пользователь существует
            from models.user import User
            user = await User.get_by_id(self.db_pool, user_id)
            if not user:
                return {"success": False, "error": "Пользователь не найден"}
            
            # Проверяем, что станция существует
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "error": "Станция не найдена"}
            
            # Проверяем, что тип ошибки существует
            error = await PowerbankError.get_by_id(self.db_pool, error_type)
            if not error:
                return {"success": False, "error": "Тип ошибки не найден"}
            
            # Проверяем, что у пользователя есть активный заказ на выдачу
            active_orders = await Order.get_active_orders_by_user(self.db_pool, user_id)
            if not active_orders:
                return {"success": False, "error": "У пользователя нет активных заказов"}
            
            # Проверяем, нет ли уже ожидающего запроса для этого пользователя
            # Используем телефон как ключ, так как в TCP обработчике ищем по телефону
            user_phone = user.phone_e164
            if user_phone in ReturnPowerbankHandler._pending_error_returns:
                return {"success": False, "error": "У пользователя уже есть ожидающий запрос на возврат с ошибкой"}
            
            # Создаем Future для Long Polling
            future = asyncio.Future()
            
            # Сохраняем запрос на возврат с ошибкой (ключ - телефон пользователя)
            timestamp = get_moscow_time()
            ReturnPowerbankHandler._pending_error_returns[user_phone] = {
                'user_id': user_id,  # Добавляем user_id для удобства
                'station_id': station_id,
                'error_type': error_type,
                'timestamp': timestamp,
                'error_name': error.type_error,
                'future': future,
                'ttl_seconds': timeout_seconds
            }
            
            
            # Ждем результат с таймаутом
            try:
                result = await asyncio.wait_for(future, timeout=timeout_seconds)
                return result
            except asyncio.TimeoutError:
                # Удаляем просроченный запрос
                if user_phone in ReturnPowerbankHandler._pending_error_returns:
                    del ReturnPowerbankHandler._pending_error_returns[user_phone]
                return {
                    "success": False, 
                    "error": f"Таймаут ожидания вставки повербанка ({timeout_seconds} секунд). Повербанк не был вставлен в станцию."
                }
            
        except Exception as e:
            # Удаляем запрос в случае ошибки
            if user_id in ReturnPowerbankHandler._pending_error_returns:
                del ReturnPowerbankHandler._pending_error_returns[user_id]
            self.logger.error(f"Ошибка обработки запроса на возврат с ошибкой: {e}")
            return {"success": False, "error": f"Ошибка обработки запроса: {str(e)}"}
    
    async def handle_powerbank_insertion(self, station_id: int, slot_number: int, powerbank_id: int) -> Dict[str, Any]:
        """
        Обрабатывает вставку повербанка в станцию.
        Проверяет, есть ли активное окно ожидания "возврата с ошибкой" для владельца павербанка на этой станции.
        Если есть - обрабатывает как возврат с ошибкой, если нет - обрабатывает как обычный возврат.
        """
        try:
            # Получаем повербанк и активный заказ
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                self.logger.error(f"Повербанк {powerbank_id} не найден")
                return {"success": False, "error": "Повербанк не найден", "handled": False}
            
            active_order = await Order.get_active_by_powerbank_serial(self.db_pool, powerbank.serial_number)
            if not active_order:
                return {"success": False, "error": "Нет активного заказа для этого повербанка", "handled": False}
            
            owner_user_phone = active_order.user_phone
            
            # Ищем активное окно ожидания "возврата с ошибкой" для владельца павербанка на этой станции
            matching_return_data = None
            matching_user_id = None
            
            # Проверяем, есть ли активное окно для владельца этого павербанка на этой станции
            for user_phone, return_data in ReturnPowerbankHandler._pending_error_returns.items():
                if (return_data.get('station_id') == station_id and 
                    user_phone == owner_user_phone):
                    # Нашли активное окно для владельца павербанка на этой станции
                    matching_return_data = return_data
                    matching_user_id = return_data.get('user_id')
                    break
            
            if matching_return_data:
                # Есть активное окно ожидания - обрабатываем как возврат с ошибкой
                error_type = matching_return_data.get('error_type')
                return await self._process_error_return(
                    station_id=station_id,
                    slot_number=slot_number,
                    powerbank_id=powerbank_id,
                    matching_user_phone=owner_user_phone,
                    matching_user_id=matching_user_id
                )
            else:
                # Нет активного окна для владельца - это обычный возврат
                # Обрабатываем обычный возврат здесь (для консистентности)
                
                # Получаем user_id владельца повербанка
                from models.user import User
                owner_user = await User.get_by_phone(self.db_pool, owner_user_phone)
                if not owner_user:
                    self.logger.error(f"Владелец повербанка с телефоном {owner_user_phone} не найден")
                    return {"success": False, "error": "Владелец повербанка не найден", "handled": False}
                
                owner_user_id = owner_user.user_id
                
                
                # Закрываем заказ как обычный возврат (без system_error)
                await active_order.update_status(self.db_pool, 'return')
                
                # Обновляем статус повербанка на активный (если он был в другом статусе)
                if powerbank.status != 'active':
                    await powerbank.update_status(self.db_pool, 'active')
                
                # Добавляем повербанк в станцию
                await StationPowerbank.add_powerbank(self.db_pool, station_id, powerbank_id, slot_number)
                
                # Обновляем remain_num станции
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    new_remain_num = int(station.remain_num) + 1
                    await station.update_remain_num(self.db_pool, new_remain_num)
                
                # Логируем действие для владельца
                await ActionLog.create(
                    self.db_pool,
                    user_id=owner_user.user_id,
                    action_type='order_update',
                    entity_type='order',
                    entity_id=active_order.order_id,
                    description='Обычный возврат повербанка'
                )
                
                # Отправляем WebSocket уведомление владельцу
                try:
                    from utils.user_notification_manager import user_notification_manager
                    await user_notification_manager.send_powerbank_return_notification(
                        user_id=owner_user.user_id,
                        order_id=active_order.order_id,
                        powerbank_serial=powerbank.serial_number,
                        message='Спасибо за возврат! Заказ успешно закрыт.'
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка отправки WebSocket уведомления: {e}")
                
                # Отправляем запрос инвентаризации в фоне без логирования
                asyncio.create_task(self._send_inventory_request_silently(station_id))
                
                
                return {
                    "success": True,
                    "handled": True,
                    "message": "Обычный возврат повербанка. Заказ успешно закрыт.",
                    "user_id": owner_user.user_id,
                    "powerbank_id": powerbank_id,
                    "station_id": station_id,
                    "slot_number": slot_number
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки вставки повербанка: {e}")
            return {"success": False, "error": f"Ошибка обработки вставки: {str(e)}", "handled": False}
    
    async def _cleanup_expired_requests(self, cleanup_interval_seconds: int = 60, max_age_minutes: int = 30):
        """
        Фоновая задача для очистки просроченных запросов на возврат с ошибкой
        """
        while True:
            await asyncio.sleep(cleanup_interval_seconds)
            current_time = get_moscow_time()
            expired_user_ids = []
            
            for user_id, request_data in self.pending_error_returns.items():
                if (current_time - request_data['timestamp']).total_seconds() > max_age_minutes * 60:
                    expired_user_ids.append(user_id)
                    
            for user_id in expired_user_ids:
                request_data = self.pending_error_returns[user_id]
                future = request_data.get('future')
                
                # Уведомляем Future о таймауте
                if future and not future.done():
                    future.set_result({
                        "success": False,
                        "error": f"Таймаут ожидания вставки повербанка ({max_age_minutes} минут)"
                    })
                
                del self.pending_error_returns[user_id]

    async def _process_error_return(self, station_id: int, slot_number: int, powerbank_id: int, matching_user_phone: str, matching_user_id: int) -> Dict[str, Any]:
        """Единая обработка успешного возврата с ошибкой: статусы, заказ, лог, future.
        
        Args:
            station_id: ID станции
            slot_number: Номер слота
            powerbank_id: ID повербанка
            matching_user_phone: Телефон пользователя (ключ в _pending_error_returns)
            matching_user_id: ID пользователя
        """
        try:
            return_data = ReturnPowerbankHandler._pending_error_returns.get(matching_user_phone, {})
            error_type = return_data.get('error_type')
            error_name = return_data.get('error_name')
            future = return_data.get('future')
            requested_station_id = return_data.get('station_id')  # Станция, на которую был запрос

            # ЗАЩИТА ОТ ДУРАКОВ ОТКЛЮЧЕНА - пользователь может вернуть в любую станцию
            # if requested_station_id and requested_station_id != station_id:
            #     error_msg = f"Пользователь {matching_user_id} попытался вернуть повербанк в станцию {station_id}, но запрос был на станцию {requested_station_id}"
            #     self.logger.warning(error_msg)
            #     if future and not future.done():
            #         future.set_result({
            #             "success": False,
            #             "error": "Повербанк должен быть возвращен в ту же станцию, где был сделан запрос"
            #         })
            #     return {"success": False, "error": "Неправильная станция для возврата"}

            # Ищем активный заказ по повербанку
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                if future and not future.done():
                    future.set_result({"error": "Повербанк не найден", "success": False})
                return {"error": "Повербанк не найден", "success": False}
            active_order = await Order.get_active_by_powerbank_serial(self.db_pool, powerbank.serial_number)
            if not active_order:
                if future and not future.done():
                    future.set_result({
                        "success": False,
                        "error": "Нет активного заказа для этого повербанка"
                    })
                return {"success": False, "error": "Нет активного заказа для этого повербанка"}

            # Получаем user_id по телефону из заказа (Order содержит user_phone, а не user_id)
            from models.user import User
            order_user = await User.get_by_phone(self.db_pool, active_order.user_phone)
            if not order_user:
                self.logger.error(f"Пользователь с телефоном {active_order.user_phone} не найден")
                if future and not future.done():
                    future.set_result({"success": False, "error": "Пользователь не найден"})
                return {"success": False, "error": "Пользователь не найден"}
            
            effective_user_id = order_user.user_id
            if effective_user_id != matching_user_id:
                pass

            # Обновляем статус повербанка и тип ошибки
            # powerbank уже получен и проверен выше на строке 309

            await powerbank.update_status(self.db_pool, 'system_error')
            await powerbank.update_power_er(self.db_pool, error_type)

            # Закрываем активный заказ
            await active_order.update_status(self.db_pool, 'return')

            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(self.db_pool, station_id, powerbank_id, slot_number)

            # Обновляем remain_num станции (при возврате повербанков становится больше)
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if station:
                new_remain_num = int(station.remain_num) + 1
                await station.update_remain_num(self.db_pool, new_remain_num)

            # Удаляем из ожидающих (используем телефон как ключ)
            if matching_user_phone in ReturnPowerbankHandler._pending_error_returns:
                del ReturnPowerbankHandler._pending_error_returns[matching_user_phone]

            # Логируем действие
            await ActionLog.create(
                self.db_pool,
                user_id=effective_user_id,
                action_type='order_update',
                entity_type='order',
                entity_id=active_order.order_id,
                description=f'Возврат повербанка с ошибкой: {error_name}'
            )

            # Получаем дополнительные данные для ответа фронтенду
            from models.station import Station
            station_obj = await Station.get_by_id(self.db_pool, station_id)
            station_box_id = station_obj.box_id if station_obj else None
            
            from models.user import User
            user_obj = await User.get_by_id(self.db_pool, effective_user_id)
            user_phone = user_obj.phone_e164 if user_obj else None
            
            # Отправляем WebSocket уведомление о возврате
            try:
                from utils.user_notification_manager import user_notification_manager
                notification_sent = await user_notification_manager.send_powerbank_return_notification(
                    user_id=effective_user_id,
                    order_id=active_order.order_id,
                    powerbank_serial=powerbank.serial_number,
                    message='Спасибо за возврат! Заказ успешно закрыт.'
                )
            except Exception as e:
                self.logger.error(f"Ошибка отправки WebSocket уведомления о возврате: {e}")
            
            result = {
                "success": True,
                "message": "Спасибо за возврат! Заказ закрыт.",
                "notification": "Спасибо за возврат! Заказ успешно закрыт.",
                "user_id": effective_user_id,
                "user_phone": user_phone,
                "powerbank_id": powerbank_id,
                "powerbank_serial": powerbank.serial_number,
                "station_id": station_id,
                "station_box_id": station_box_id,
                "slot_number": slot_number,
                "error_type": error_type,
                "error_name": error_name
            }

            if future and not future.done():
                future.set_result(result)
            
            # Отправляем запрос инвентаризации в фоне без логирования
            asyncio.create_task(self._send_inventory_request_silently(station_id))

            return result
        except Exception as e:
            self.logger.error(f"Ошибка обработки возврата с ошибкой: {e}")
            return {"success": False, "error": f"Ошибка обработки: {str(e)}"}
    
    async def get_pending_error_returns(self) -> Dict[int, Dict[str, Any]]:
        """
        Получает список ожидающих возврат с ошибкой
        """
        return ReturnPowerbankHandler._pending_error_returns.copy()
    
    async def cancel_error_return(self, user_id: int) -> Dict[str, Any]:
        """
        Отменяет ожидание возврата с ошибкой
        """
        try:
            if user_id in ReturnPowerbankHandler._pending_error_returns:
                del ReturnPowerbankHandler._pending_error_returns[user_id]
                return {"success": True, "message": "Запрос на возврат с ошибкой отменен"}
            else:
                return {"success": False, "error": "Запрос на возврат с ошибкой не найден"}
                
        except Exception as e:
            self.logger.error(f"Ошибка отмены запроса на возврат: {e}")
            return {"success": False, "error": f"Ошибка отмены: {str(e)}"}
    
    async def cleanup_expired_requests(self, max_age_minutes: int = 30) -> int:
        """
        Очищает просроченные запросы на возврат с ошибкой
        """
        try:
            current_time = get_moscow_time()
            expired_users = []
            
            for user_id, return_data in ReturnPowerbankHandler._pending_error_returns.items():
                age_minutes = (current_time - return_data['timestamp']).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del ReturnPowerbankHandler._pending_error_returns[user_id]
            
            return len(expired_users)
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки просроченных запросов: {e}")
            return 0
    
    async def get_error_types(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных типов ошибок
        """
        try:
            errors = await PowerbankError.get_all(self.db_pool)
            return [error.to_dict() for error in errors]
        except Exception as e:
            self.logger.error(f"Ошибка получения типов ошибок: {e}")
            return []
    
    async def handle_tcp_error_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает TCP запрос на возврат повербанка с ошибкой от станции (команда 0x66)
        Только для случаев, когда есть ожидающий возврат с ошибкой пользователь
        """
        try:
            from utils.packet_utils import parse_return_power_bank_request, build_return_power_bank_response
            from utils.station_resolver import get_station_id_by_box_id
            from models.powerbank import Powerbank
            
            # Парсим данные запроса
            parsed_data = parse_return_power_bank_request(data)
            
            if 'error' in parsed_data:
                self.logger.error(f"Ошибка парсинга запроса возврата: {parsed_data['error']}")
                return None
            
            slot = parsed_data.get('Slot')
            terminal_id = parsed_data.get('TerminalID')
            level = parsed_data.get('Level', 0)
            voltage = parsed_data.get('Voltage', 0)
            current = parsed_data.get('Current', 0)
            temperature = parsed_data.get('Temperature', 0)
            status = parsed_data.get('Status', 0)
            soh = parsed_data.get('SOH', 0)

            # Версия протокола (VSN) берём из пакета
            vsn = parsed_data.get('VSN', 1)
            
            # Получаем ID станции
            station_id = await get_station_id_by_box_id(self.db_pool, connection.box_id)
            if not station_id:
                self.logger.error(f"Станция с box_id {connection.box_id} не найдена")
                return None
            
            # Ищем повербанк по terminal_id
            powerbank = await Powerbank.get_by_terminal_id(self.db_pool, terminal_id)
            if not powerbank:
                self.logger.error(f"Повербанк с terminal_id {terminal_id} не найден")
                # Отправляем ответ об ошибке
                return build_return_power_bank_response(
                    slot=slot,
                    result=0,  # Ошибка
                    terminal_id=terminal_id.encode('ascii'),
                    level=level,
                    voltage=voltage,
                    current=current,
                    temperature=temperature,
                    status=status,
                    soh=soh,
                    vsn=vsn,
                    token=connection.token
                )
            
            powerbank_id = powerbank.powerbank_id

            # Получаем активный заказ по повербанку
            try:
                active_order = await Order.get_active_by_powerbank_serial(self.db_pool, powerbank.serial_number)
            except Exception:
                active_order = None

            if not active_order:
                return None

            owner_user_phone = active_order.user_phone
            
            # Ищем активное окно ожидания "возврата с ошибкой" для владельца павербанка на этой станции
            matching_return_data = None
            matching_user_id = None
            error_type = None
            
            # Проверяем, есть ли активное окно для владельца этого павербанка на этой станции
            for user_phone, return_data in self.pending_error_returns.items():
                if (return_data.get('station_id') == station_id and 
                    user_phone == owner_user_phone):
                    # Нашли активное окно для владельца павербанка на этой станции
                    matching_return_data = return_data
                    matching_user_id = return_data.get('user_id')
                    error_type = return_data.get('error_type')
                    break
            
            if not matching_return_data:
                # Нет активного окна для владельца павербанка - это обычный возврат
                # Возвращаем None для обычной обработки
                return None
            
            # Есть активное окно - обрабатываем как возврат с ошибкой
            matching_user_phone = owner_user_phone
            
            
            # Получаем user_id по телефону (уже есть в matching_user_id, но проверяем для безопасности)
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT user_id FROM app_user WHERE phone_e164 = %s
                    """, (matching_user_phone,))
                    user_result = await cur.fetchone()
                    if not user_result:
                        self.logger.error(f"Пользователь с телефоном {matching_user_phone} не найден")
                        return build_return_power_bank_response(
                            slot=slot,
                            result=0,
                            terminal_id=terminal_id.encode('ascii'),
                            level=level,
                            voltage=voltage,
                            current=current,
                            temperature=temperature,
                            status=status,
                            soh=soh,
                            vsn=vsn,
                            token=connection.token
                        )
                    user_id = user_result[0]
            
            # Обрабатываем как возврат с ошибкой
            await self._process_error_return(
                station_id=station_id,
                slot_number=slot,
                powerbank_id=powerbank_id,
                matching_user_phone=matching_user_phone,
                matching_user_id=user_id
            )
            
            return build_return_power_bank_response(
                slot=slot,
                result=1,
                terminal_id=terminal_id.encode('ascii'),
                level=level,
                voltage=voltage,
                current=current,
                temperature=temperature,
                status=status,
                soh=soh,
                vsn=vsn,
                token=connection.token
            )
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки запроса возврата с ошибкой: {e}")
            return None
