"""
Обработчик для выдачи повербанков
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from utils.packet_utils import build_borrow_power_bank, parse_borrow_request, parse_borrow_response
from utils.centralized_logger import get_logger


class BorrowPowerbankHandler:
    """Обработчик для выдачи повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('borrow_powerbank')
        # Словарь для ожидания ответов от станций: {order_id: asyncio.Future}
        self.pending_requests = {}
    
    async def handle_borrow_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на выдачу повербанка
        """
        try:
            # Парсим запрос на выдачу
            borrow_request = parse_borrow_request(data)
            print(f"Обработан запрос на выдачу: слот {borrow_request['Slot']}")
            
            # Получаем информацию о станции
            station_id = connection.station_id
            if not station_id:
                print("Станция не найдена для соединения")
                return None
            
            requested_slot = borrow_request['Slot']
            
            # Проверяем, есть ли повербанк в запрашиваемом слоте
            station_powerbank = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, requested_slot
            )
            
            if not station_powerbank:
                print(f"В слоте {requested_slot} станции {station_id} нет повербанка")
                return None
            
            # Проверяем, что повербанк активен
            powerbank = await Powerbank.get_by_id(self.db_pool, station_powerbank.powerbank_id)
            if not powerbank or powerbank.status != 'active':
                print(f"Повербанк в слоте {requested_slot} не активен")
                return None
            
            # Проверяем, что повербанк не выдан повторно (защита от дублирования)
            if await self._is_powerbank_already_borrowed(powerbank.powerbank_id):
                print(f"Повербанк {powerbank.serial_number} уже выдан и не может быть выдан повторно")
                return None
            
            # Дополнительная проверка: убеждаемся, что повербанк все еще в станции
            if not await self._is_powerbank_in_station(station_id, powerbank.powerbank_id):
                print(f"Повербанк {powerbank.serial_number} больше не находится в станции")
                return None
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для команды выдачи")
                return None
            
            # Создаем команду на выдачу повербанка
            borrow_command = build_borrow_power_bank(
                secret_key=secret_key,
                slot=requested_slot,
                vsn=borrow_request['VSN']
            )
            
            print(f"Создана команда на выдачу повербанка из слота {requested_slot}")
            return borrow_command
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
    
    async def handle_borrow_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ от станции на выдачу повербанка
        """
        try:
            # Парсим ответ от станции
            borrow_response = parse_borrow_response(data)
            print(f"Обработан ответ на выдачу: {borrow_response}")
            
            station_id = connection.station_id
            if not station_id:
                return
            
            slot_number = borrow_response.get('Slot', 0)
            success = borrow_response.get('Success', False)
            
            # Ищем соответствующий pending request
            pending_order_id = None
            for order_id, request_info in self.pending_requests.items():
                if (request_info['station_id'] == station_id and 
                    request_info['slot_number'] == slot_number):
                    pending_order_id = order_id
                    break
            
            # Проверяем успешность ответа
            if success:
                print("Выдача повербанка успешна")
                
                # Получаем информацию о повербанке из слота
                station_powerbank = await StationPowerbank.get_by_slot(
                    self.db_pool, station_id, slot_number
                )
                
                if station_powerbank:
                    # Удаляем повербанк из станции
                    await self.process_successful_borrow(station_id, slot_number)
                
                # Обновляем last_seen станции
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    # Обновляем remain_num станции (уменьшаем на 1 при выдаче)
                    await station.update_remain_num(self.db_pool, int(station.remain_num) - 1)
                
                print(f"Выдача повербанка успешна для станции {station_id}")
                
                # Уведомляем ожидающий запрос об успехе
                if pending_order_id and pending_order_id in self.pending_requests:
                    future = self.pending_requests[pending_order_id]['future']
                    if not future.done():
                        future.set_result({"success": True, "message": "Повербанк успешно выдан"})
                    del self.pending_requests[pending_order_id]
                
                
            else:
                
                # Дополнительная информация о причине неудачи не предоставляется
                error_msg = "Станция отклонила выдачу повербанка"
                
                # Получаем дополнительную информацию из ответа
                terminal_id = borrow_response.get('TerminalID', 'unknown')
                current_slot_locked = borrow_response.get('CurrentSlotLockStatus', 0)
                adjacent_slot_locked = borrow_response.get('AdjacentSlotLockStatus', 0)
                
                # Формируем более детальное сообщение об ошибке
                if current_slot_locked:
                    error_msg = "Слот заблокирован"
                elif terminal_id == '0000000000000000':
                    error_msg = "Слот пуст"
                else:
                    error_msg = "Ошибка выдачи повербанка"
                
                self.logger.error(f"Выдача повербанка не удалась для станции {station_id}, слот {slot_number}: {error_msg}")
                
                # Уведомляем ожидающий запрос об ошибке
                if pending_order_id and pending_order_id in self.pending_requests:
                    future = self.pending_requests[pending_order_id]['future']
                    if not future.done():
                        future.set_result({"success": False, "message": error_msg})
                    del self.pending_requests[pending_order_id]
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def process_successful_borrow(self, station_id: int, slot_number: int) -> None:
        """
        Обрабатывает успешную выдачу повербанка

        """
        try:
            success = await StationPowerbank.remove_powerbank(
                self.db_pool, station_id, slot_number
            )
            
            if success:
                print(f"Повербанк успешно удален из слота {slot_number} станции {station_id}")
            else:
                print(f"Не удалось удалить повербанк из слота {slot_number}")
                
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def _create_borrow_order(self, station_id: int, powerbank_id: int, user_id: int) -> None:
        """
        Создает запись о выдаче повербанка в таблице orders
        """
        try:
            await Order.create_borrow_order(
                self.db_pool, station_id, user_id, powerbank_id
            )
            print(f"Создан заказ на выдачу повербанка {powerbank_id} пользователю {user_id}")
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def get_available_slots(self, station_id: int) -> list:
        """
        Получает список доступных слотов для выдачи
        """
        try:
            slots = await StationPowerbank.get_station_slots(self.db_pool, station_id)
            return slots
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return []
    
    async def _is_powerbank_already_borrowed(self, powerbank_id: int) -> bool:
        """
        Проверяет, не выдан ли уже повербанк (защита от повторной выдачи)
        """
        try:
            # Проверяем, есть ли активный заказ на выдачу этого повербанка
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT COUNT(*) as count 
                        FROM orders 
                        WHERE powerbank_id = %s 
                        AND status = 'borrow' 
                        AND timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    """, (powerbank_id,))
                    
                    result = await cur.fetchone()
                    return result[0] > 0
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return False
    
    async def _is_powerbank_in_station(self, station_id: int, powerbank_id: int) -> bool:
        """
        Проверяет, что повербанк все еще находится в станции
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT COUNT(*) as count 
                        FROM station_powerbank 
                        WHERE station_id = %s AND powerbank_id = %s
                    """, (station_id, powerbank_id))
                    
                    result = await cur.fetchone()
                    return result[0] > 0
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return False
    
    async def send_borrow_request_and_wait(self, station_id: int, powerbank_id: int, user_id: int, order_id: int) -> Dict[str, Any]:
        """
        Отправляет запрос на выдачу повербанка на станцию и ждет ответа
        """
        import asyncio
        from datetime import datetime, timedelta
        
        try:
            # Получаем соединение со станцией
            if not self.connection_manager:
                return {"success": False, "message": "Connection manager недоступен"}
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"success": False, "message": "Станция не подключена"}
            
            # Проверяем онлайн статус станции (последний heartbeat должен быть не более 30 секунд назад)
            if connection.last_heartbeat:
                from utils.time_utils import get_moscow_time
                time_since_heartbeat = (get_moscow_time() - connection.last_heartbeat).total_seconds()
                if time_since_heartbeat > 30:
                    return {"success": False, "message": f"Станция офлайн (последний heartbeat {time_since_heartbeat:.0f} секунд назад)"}
            else:
                return {"success": False, "message": "Станция не отправляла heartbeat"}
            
            # Получаем информацию о повербанке и его слоте
            station_powerbank = await StationPowerbank.get_by_powerbank_id(self.db_pool, powerbank_id)
            if not station_powerbank:
                return {"success": False, "message": "Повербанк не найден в станции"}
            
            slot_number = station_powerbank.slot_number
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                return {"success": False, "message": "Нет секретного ключа для команды выдачи"}
            
            # Создаем Future для ожидания ответа
            future = asyncio.Future()
            self.pending_requests[order_id] = {
                'future': future,
                'station_id': station_id,
                'slot_number': slot_number,
                'powerbank_id': powerbank_id,
                'user_id': user_id
            }
            
            # Создаем команду на выдачу повербанка
            borrow_command = build_borrow_power_bank(
                secret_key=secret_key,
                slot=slot_number,
                vsn=1  # Используем VSN=1 по умолчанию
            )
            
            # Отправляем команду через TCP соединение
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(borrow_command)
                await connection.writer.drain()
                print(f" Команда на выдачу повербанка отправлена станции {station_id}, слот {slot_number}")
                
                # Ждем ответа от станции (максимум 15 секунд)
                try:
                    result = await asyncio.wait_for(future, timeout=15.0)
                    return result
                except asyncio.TimeoutError:
                    # Убираем из pending_requests при таймауте
                    if order_id in self.pending_requests:
                        del self.pending_requests[order_id]
                    
                    # Логируем таймаут с деталями
                    self.logger.error(f"Таймаут ожидания ответа от станции {station_id} для слота {slot_number}, заказ {order_id}")
                    return {"success": False, "message": "Таймаут ожидания ответа от станции (15 секунд)"}
                
            else:
                # Убираем из pending_requests если соединение недоступно
                if order_id in self.pending_requests:
                    del self.pending_requests[order_id]
                return {"success": False, "message": "TCP соединение со станцией недоступно"}
                
        except Exception as e:
            # Убираем из pending_requests при ошибке
            if order_id in self.pending_requests:
                del self.pending_requests[order_id]
            print(f" Ошибка отправки запроса на выдачу: {e}")
            return {"success": False, "message": f"Ошибка отправки команды: {str(e)}"}

    async def send_borrow_request(self, station_id: int, powerbank_id: int, user_id: int) -> Dict[str, Any]:
        """
        Отправляет запрос на выдачу повербанка на станцию (старый метод для совместимости)
        """
        try:
            
            # Получаем соединение со станцией
            if not self.connection_manager:
                return {"success": False, "message": "Connection manager недоступен"}
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"success": False, "message": "Станция не подключена"}
            
            # Получаем информацию о повербанке и его слоте
            station_powerbank = await StationPowerbank.get_by_powerbank_id(self.db_pool, powerbank_id)
            if not station_powerbank:
                return {"success": False, "message": "Повербанк не найден в станции"}
            
            slot_number = station_powerbank.slot_number
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                return {"success": False, "message": "Нет секретного ключа для команды выдачи"}
            
            # Создаем команду на выдачу повербанка
            borrow_command = build_borrow_power_bank(
                secret_key=secret_key,
                slot=slot_number,
                vsn=1  # Используем VSN=1 по умолчанию
            )
            
            # Отправляем команду через TCP соединение
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(borrow_command)
                await connection.writer.drain()
                print(f" Команда на выдачу повербанка отправлена станции {station_id}, слот {slot_number}")
                
                return {
                    "success": True,
                    "message": f"Команда на выдачу повербанка отправлена на станцию",
                    "packet_hex": borrow_command.hex().upper()
                }
            else:
                return {"success": False, "message": "TCP соединение со станцией недоступно"}
                
        except Exception as e:
            print(f" Ошибка отправки запроса на выдачу: {e}")
            return {"success": False, "message": f"Ошибка отправки команды: {str(e)}"}

    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции с повербанком
        """
        try:
            from utils.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(self.db_pool)
            
            # Получаем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                print(f"Соединение со станцией {station_id} не найдено")
                return
            
            await inventory_manager.request_inventory_after_operation(station_id, connection)
            print(f" Запрос инвентаря отправлен после операции выдачи")
            
        except Exception as e:
            print(f" Ошибка запроса инвентаря после операции: {e}")
