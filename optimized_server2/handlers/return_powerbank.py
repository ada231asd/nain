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
        # Словарь для ожидания возврата с ошибкой: {user_id: {'station_id': int, 'error_type': int, 'timestamp': datetime, 'future': asyncio.Future}}
        self.pending_error_returns = {}
        # Запускаем фоновую задачу для очистки просроченных запросов
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
            if user_id in self.pending_error_returns:
                return {"success": False, "error": "У пользователя уже есть ожидающий запрос на возврат с ошибкой"}
            
            # Создаем Future для Long Polling
            future = asyncio.Future()
            
            # Сохраняем запрос на возврат с ошибкой
            self.pending_error_returns[user_id] = {
                'station_id': station_id,
                'error_type': error_type,
                'timestamp': get_moscow_time(),
                'error_name': error.type_error,
                'future': future
            }
            
            self.logger.info(f"Пользователь {user_id} запросил возврат с ошибкой типа {error_type} в станцию {station_id}. Ожидаем вставки повербанка...")
            
            # Ждем результат с таймаутом
            try:
                result = await asyncio.wait_for(future, timeout=timeout_seconds)
                return result
            except asyncio.TimeoutError:
                # Удаляем просроченный запрос
                if user_id in self.pending_error_returns:
                    del self.pending_error_returns[user_id]
                return {
                    "success": False, 
                    "error": f"Таймаут ожидания вставки повербанка ({timeout_seconds} секунд). Повербанк не был вставлен в станцию."
                }
            
        except Exception as e:
            # Удаляем запрос в случае ошибки
            if user_id in self.pending_error_returns:
                del self.pending_error_returns[user_id]
            self.logger.error(f"Ошибка обработки запроса на возврат с ошибкой: {e}")
            return {"success": False, "error": f"Ошибка обработки запроса: {str(e)}"}
    
    async def handle_powerbank_insertion(self, station_id: int, slot_number: int, powerbank_id: int) -> Dict[str, Any]:
        """
        Обрабатывает вставку повербанка в станцию
        Сопоставляет с ожидающими возврат пользователями и уведомляет Future
        """
        try:
            # Ищем пользователя, который ожидает возврат в эту станцию
            matching_user_id = None
            for user_id, return_data in self.pending_error_returns.items():
                if return_data['station_id'] == station_id:
                    matching_user_id = user_id
                    break
            
            if not matching_user_id:
                self.logger.debug(f"Повербанк {powerbank_id} вставлен в станцию {station_id}, но нет ожидающих возврат пользователей")
                return {"success": False, "error": "Нет ожидающих возврат пользователей для этой станции"}
            
            # Получаем данные о возврате
            return_data = self.pending_error_returns[matching_user_id]
            error_type = return_data['error_type']
            future = return_data.get('future')
            
            # Проверяем, что повербанк принадлежит пользователю
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if not active_order or active_order.user_id != matching_user_id:
                self.logger.warning(f"Повербанк {powerbank_id} не принадлежит пользователю {matching_user_id}")
                if future and not future.done():
                    future.set_result({
                        "success": False, 
                        "error": "Повербанк не принадлежит ожидающему пользователю"
                    })
                return {"success": False, "error": "Повербанк не принадлежит ожидающему пользователю"}
            
            # Обновляем статус повербанка на системную ошибку
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "error": "Повербанк не найден"}
            
            # Обновляем статус повербанка
            await powerbank.update_status(self.db_pool, 'system_error')
            
            # Обновляем поле power_er (тип ошибки)
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE powerbank SET power_er = %s WHERE id = %s",
                        (error_type, powerbank_id)
                    )
            
            # Закрываем активный заказ
            await Order.update_order_status(self.db_pool, active_order.order_id, 'return')
            
            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank_id, slot_number
            )
            
            # Удаляем из ожидающих возврат
            del self.pending_error_returns[matching_user_id]
            
            # Логируем действие
            await ActionLog.create_log(
                self.db_pool, matching_user_id, 'order_update', 'order', 
                active_order.order_id, f'Возврат повербанка с ошибкой: {return_data["error_name"]}'
            )
            
            self.logger.info(f"Повербанк {powerbank_id} успешно возвращен с ошибкой типа {error_type} пользователем {matching_user_id}")
            
            # Уведомляем Future о успешном результате
            result = {
                "success": True,
                "message": f"Повербанк успешно возвращен с ошибкой",
                "user_id": matching_user_id,
                "powerbank_id": powerbank_id,
                "station_id": station_id,
                "slot_number": slot_number,
                "error_type": error_type,
                "error_name": return_data['error_name']
            }
            
            if future and not future.done():
                future.set_result(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки вставки повербанка: {e}")
            return {"success": False, "error": f"Ошибка обработки вставки: {str(e)}"}
    
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
                self.logger.info(f"Просроченный запрос на возврат с ошибкой для пользователя {user_id} удален")
    
    async def get_pending_error_returns(self) -> Dict[int, Dict[str, Any]]:
        """
        Получает список ожидающих возврат с ошибкой
        """
        return self.pending_error_returns.copy()
    
    async def cancel_error_return(self, user_id: int) -> Dict[str, Any]:
        """
        Отменяет ожидание возврата с ошибкой
        """
        try:
            if user_id in self.pending_error_returns:
                del self.pending_error_returns[user_id]
                self.logger.info(f"Отменен запрос на возврат с ошибкой для пользователя {user_id}")
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
            
            for user_id, return_data in self.pending_error_returns.items():
                age_minutes = (current_time - return_data['timestamp']).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.pending_error_returns[user_id]
                self.logger.info(f"Удален просроченный запрос на возврат для пользователя {user_id}")
            
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
    
    async def handle_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на возврат повербанка от станции (команда 0x66)
        """
        try:
            from utils.packet_utils import parse_return_power_bank_request, build_return_power_bank_response
            from utils.station_resolver import get_station_id_by_box_id
            from models.station import Station
            from models.powerbank import Powerbank
            from models.order import Order
            from utils.time_utils import get_moscow_time
            
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
            
            self.logger.info(f"Получен запрос на возврат повербанка: слот {slot}, terminal_id {terminal_id}")
            
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
                    vsn=connection.vsn,
                    token=connection.token
                )
            
            # Проверяем, есть ли ожидающий возврат с ошибкой для этого повербанка
            powerbank_id = powerbank.powerbank_id
            matching_user_id = None
            error_type = None
            
            for user_id, return_data in self.pending_error_returns.items():
                if (return_data['station_id'] == station_id and 
                    return_data['powerbank_id'] == powerbank_id):
                    matching_user_id = user_id
                    error_type = return_data['error_type']
                    break
            
            if matching_user_id:
                # Обрабатываем возврат с ошибкой
                self.logger.info(f"Обрабатываем возврат с ошибкой для пользователя {matching_user_id}, повербанк {powerbank_id}")
                
                # Обновляем статус повербанка
                await powerbank.update_status(self.db_pool, 'system_error')
                await powerbank.update_power_er(self.db_pool, error_type)
                
                # Закрываем активный заказ
                active_order = await Order.get_active_borrow_order(self.db_pool, powerbank_id)
                if active_order:
                    await active_order.update_order_status(self.db_pool, 'return')
                    self.logger.info(f"Активный заказ {active_order.order_id} закрыт")
                
                # Удаляем из ожидающих
                del self.pending_error_returns[matching_user_id]
                
                self.logger.info(f"Повербанк {powerbank_id} успешно возвращен с ошибкой типа {error_type}")
                
                # Отправляем успешный ответ
                return build_return_power_bank_response(
                    slot=slot,
                    result=1,  # Успех
                    terminal_id=terminal_id.encode('ascii'),
                    level=level,
                    voltage=voltage,
                    current=current,
                    temperature=temperature,
                    status=status,
                    soh=soh,
                    vsn=connection.vsn,
                    token=connection.token
                )
            else:
                # Обычный возврат без ошибки
                self.logger.info(f"Обычный возврат повербанка {powerbank_id} в станцию {station_id}")
                
                # Обновляем статус повербанка на "в станции"
                await powerbank.update_status(self.db_pool, 'in_station')
                
                # Закрываем активный заказ
                active_order = await Order.get_active_borrow_order(self.db_pool, powerbank_id)
                if active_order:
                    await active_order.update_order_status(self.db_pool, 'return')
                    self.logger.info(f"Активный заказ {active_order.order_id} закрыт")
                
                # Отправляем успешный ответ
                return build_return_power_bank_response(
                    slot=slot,
                    result=1,  # Успех
                    terminal_id=terminal_id.encode('ascii'),
                    level=level,
                    voltage=voltage,
                    current=current,
                    temperature=temperature,
                    status=status,
                    soh=soh,
                    vsn=connection.vsn,
                    token=connection.token
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки запроса возврата: {e}")
            return None
