"""
Обработчик для возврата повербанков
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from utils.centralized_logger import get_logger
from utils.packet_utils import build_return_power_bank, parse_return_response, get_moscow_time


class ReturnPowerbankHandler:
    """Обработчик для возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_return_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ от станции на возврат повербанка
        """
        try:
            # Парсим ответ от станции
            return_response = parse_return_response(data)
            logger = get_logger('return_powerbank')
            logger.info(f"Обработан ответ на возврат: {return_response}")
            
            station_id = connection.station_id
            if not station_id:
                return
            
            # Получаем информацию о повербанке из слота
            slot_number = return_response.get('Slot', 0)
            terminal_id = return_response.get('TerminalID', '')
            success = return_response.get('Success', False)
            result_code = return_response.get('ResultCode', 0)
            
            # Если есть TerminalID, значит повербанк вставлен в станцию
            if terminal_id:
                logger.info(f"Повербанк {terminal_id} вставлен в станцию {station_id}, слот {slot_number}")
                
                # Получаем информацию о повербанке из слота станции
                from models.station_powerbank import StationPowerbank
                station_powerbank = await StationPowerbank.get_by_station_and_slot(self.db_pool, station_id, slot_number)
                
                if station_powerbank:
                    # Есть повербанк в слоте - проверяем активные заказы
                    logger.info(f"Повербанк {station_powerbank.powerbank_id} найден в слоте {slot_number}")
                    
                    # Ищем активный заказ на выдачу для этого повербанка
                    active_order = await Order.get_active_borrow_order(self.db_pool, station_powerbank.powerbank_id)
                    
                    if active_order:
                        # Есть активный заказ - меняем статус на 'return' (закрываем)
                        await Order.update_order_status(self.db_pool, active_order.order_id, 'return')
                        logger.info(f"Заказ {active_order.order_id} изменен на статус 'return' - повербанк {station_powerbank.powerbank_id} возвращен")
                    else:
                        logger.info(f"Активный заказ для повербанка {station_powerbank.powerbank_id} не найден")
                else:
                    logger.warning(f"Повербанк не найден в слоте {slot_number} станции {station_id}")
                
                # Обновляем last_seen станции
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    # Обновляем remain_num станции (увеличиваем на 1 при возврате)
                    await station.update_remain_num(self.db_pool, int(station.remain_num) + 1)
                
                logger.info(f"Возврат повербанка обработан для станции {station_id} (успех: {success})")
                
                # Запрашиваем инвентарь только при успешном возврате для обновления данных
                if success:
                    await self._request_inventory_after_operation(station_id)
                
            else:
                # Нет TerminalID - повербанк не вставлен
                error_messages = {
                    68: "Повербанк не найден в слоте",
                    1: "Слот заблокирован",
                    2: "Повербанк уже в слоте", 
                    3: "Ошибка связи со станцией",
                    4: "Неверный слот",
                    5: "Повербанк поврежден"
                }
                error_msg = error_messages.get(result_code, f"Неизвестная ошибка (код: {result_code})")
                logger.warning(f"Возврат повербанка не удался для станции {station_id}: {error_msg}")
                    
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка обработки возврата: {e}")
    
    async def _update_or_add_powerbank_to_station(self, station_id: int, powerbank_id: int, slot_number: int) -> None:
        """
        Обновляет или добавляет повербанк в станцию
        """
        try:
            # Проверяем, есть ли уже повербанк в этом слоте
            existing = await StationPowerbank.get_by_station_and_slot(self.db_pool, station_id, slot_number)
            
            if existing:
                # Обновляем существующий повербанк
                await StationPowerbank.update_powerbank_data(
                    self.db_pool, 
                    station_id, 
                    slot_number, 
                    level=100, 
                    voltage=4200, 
                    temperature=25
                )
                
                logger = get_logger('return_powerbank')
                logger.info(f"Обновлены данные повербанка {powerbank_id} в слоте {slot_number} станции {station_id}")
            else:
                # Добавляем новый повербанк в станцию
                await self._add_powerbank_to_station(station_id, powerbank_id, slot_number)
                
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка обновления/добавления повербанка в станцию: {e}")
    
    async def _add_powerbank_to_station(self, station_id: int, powerbank_id: int, slot_number: int) -> None:
        """
        Добавляет повербанк в станцию
        """
        try:
            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(
                self.db_pool, 
                station_id, 
                powerbank_id, 
                slot_number, 
                level=100, 
                voltage=4200, 
                temperature=25
            )
            
            logger = get_logger('return_powerbank')
            logger.info(f"Повербанк {powerbank_id} добавлен в станцию {station_id}, слот {slot_number}")
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка добавления повербанка в станцию: {e}")
    
    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции
        """
        try:
            from handlers.query_inventory import QueryInventoryHandler
            inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            await inventory_handler.send_inventory_request(station_id)
            
            logger = get_logger('return_powerbank')
            logger.info(f"Запрос инвентаря отправлен на станцию {station_id}")
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка запроса инвентаря: {e}")
    
    async def start_damage_return_process(self, station_id: int, user_id: int, description: str) -> Dict[str, Any]:
        """
        Запускает процесс возврата повербанка с поломкой
        """
        try:
            logger = get_logger('return_powerbank')
            logger.info(f"Начинаем процесс возврата с поломкой: station_id={station_id}, user_id={user_id}")
            
            # Проверяем, что станция существует и активна
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "message": "Станция не найдена"}
            
            if station.status != 'active':
                return {"success": False, "message": "Станция неактивна"}
            
            # Проверяем, что станция была онлайн в течение последних 30 секунд
            from utils.station_utils import validate_station_for_operation
            station_valid, station_message = await validate_station_for_operation(
                self.db_pool, self.connection_manager, station_id, "возврат powerbank'а с поломкой", 30
            )
            
            if not station_valid:
                return {"success": False, "message": station_message}
            
            # Получаем соединение (уже проверенное в validate_station_for_operation)
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            
            # Ищем активный заказ пользователя
            active_orders = await Order.get_active_orders_by_user(self.db_pool, user_id)
            if not active_orders:
                return {"success": False, "message": "У вас нет активных заказов"}
            
            # Берем первый активный заказ (можно расширить логику выбора)
            active_order = active_orders[0]
            powerbank_id = active_order.powerbank_id
            
            if not powerbank_id:
                return {"success": False, "message": "В заказе не указан повербанк"}
            
            # Получаем информацию о повербанке
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "message": "Повербанк не найден"}
            
            # Обновляем статус повербанка на "сломанный пользователем"
            await powerbank.update_status(self.db_pool, 'user_reported_broken')
            await powerbank.update_write_off_reason(self.db_pool, 'broken')
            
            # Создаем заказ на возврат с поломкой
            return_order = await Order.create_return_order(
                self.db_pool, 
                station_id, 
                user_id, 
                powerbank_id
            )
            
            # Обновляем оригинальный заказ на статус "возвращен с поломкой"
            await Order.update_order_status(self.db_pool, active_order.order_id, 'return_damage')
            
            # Создаем запись об ошибке повербанка
            from api.powerbank_error_report_api import PowerbankErrorReportAPI
            error_api = PowerbankErrorReportAPI(self.db_pool)
            await error_api.report_powerbank_error(
                order_id=active_order.order_id,
                powerbank_id=powerbank_id,
                station_id=station_id,
                user_id=user_id,
                error_type='other',  
                additional_notes=description
            )
            
            # Отправляем команду на возврат повербанка
            secret_key = connection.secret_key
            if not secret_key:
                return {"success": False, "message": "Нет секретного ключа для станции"}
            
            # Находим свободный слот для возврата
            free_slot = await self._find_free_slot(station_id)
            if not free_slot:
                return {"success": False, "message": "Нет свободных слотов для возврата"}
            
            # Создаем команду возврата
            return_command = build_return_power_bank(
                secret_key=secret_key,
                slot=free_slot,
                vsn=1
            )
            
            # Отправляем команду станции
            try:
                connection.writer.write(return_command)
                await connection.writer.drain()
                logger.info(f"Команда возврата отправлена на станцию {station_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки команды возврата: {e}")
                return {"success": False, "message": f"Ошибка отправки команды: {e}"}
            
            # Ждем 10 секунд для вставки повербанка пользователем
            logger.info(f"Ожидаем вставку повербанка в течение 10 секунд...")
            await asyncio.sleep(10)
            
            # Запрашиваем инвентарь для получения актуальных данных о вставленном повербанке
            await self._request_inventory_after_operation(station_id)
            await asyncio.sleep(2)
            
            # Проверяем, был ли повербанк действительно вставлен в станцию
            powerbank_inserted = await self._check_powerbank_insertion(station_id, powerbank_id)
            
            if powerbank_inserted:
                logger.info(f"Повербанк {powerbank_id} успешно вставлен в станцию {station_id}")
                message = "Повербанк возвращен с поломкой и успешно обработан станцией."
            else:
                logger.warning(f"Повербанк {powerbank_id} не был обнаружен в станции {station_id} после 10 секунд ожидания")
                message = "Повербанк возвращен с поломкой, но не был обнаружен в станции. Проверьте, что повербанк вставлен правильно."
            
            logger.info(f"Процесс возврата с поломкой завершен: order_id={return_order.order_id}")
            
            return {
                "success": True,
                "message": message,
                "order_id": return_order.order_id,
                "powerbank_id": powerbank_id,
                "station_id": station_id,
                "powerbank_inserted": powerbank_inserted
            }
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка процесса возврата с поломкой: {e}")
            return {"success": False, "message": f"Ошибка процесса возврата: {e}"}
    
    async def _check_powerbank_insertion(self, station_id: int, powerbank_id: int) -> bool:
        """
        Проверяет, был ли повербанк вставлен в станцию
        """
        try:
            # Проверяем, есть ли повербанк в station_powerbank для этой станции
            station_powerbanks = await StationPowerbank.get_by_station(self.db_pool, station_id)
            
            for sp in station_powerbanks:
                if sp.powerbank_id == powerbank_id:
                    logger = get_logger('return_powerbank')
                    logger.info(f"Повербанк {powerbank_id} найден в слоте {sp.slot_number} станции {station_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка проверки вставки повербанка: {e}")
            return False
    
    async def start_manual_return_process(self, station_id: int, user_id: int, order_id: int) -> Dict[str, Any]:
        """
        Запускает процесс ручного возврата повербанка (вариант 3)
        """
        try:
            logger = get_logger('return_powerbank')
            logger.info(f"Начинаем процесс ручного возврата: station_id={station_id}, user_id={user_id}, order_id={order_id}")
            
            # Получаем заказ
            order = await Order.get_by_id(self.db_pool, order_id)
            if not order:
                return {"success": False, "message": "Заказ не найден"}
            
            if order.user_id != user_id:
                return {"success": False, "message": "Заказ не принадлежит пользователю"}
            
            if order.status != 'borrow':
                return {"success": False, "message": "Заказ неактивен или уже возвращен"}
            
            powerbank_id = order.powerbank_id
            if not powerbank_id:
                return {"success": False, "message": "В заказе не указан повербанк"}
            
            # Проверяем, что станция существует и активна
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "message": "Станция не найдена"}
            
            if station.status != 'active':
                return {"success": False, "message": "Станция неактивна"}
            
            # Проверяем, что станция была онлайн в течение последних 30 секунд
            from utils.station_utils import validate_station_for_operation
            station_valid, station_message = await validate_station_for_operation(
                self.db_pool, self.connection_manager, station_id, "ручной возврат powerbank'а", 30
            )
            
            if not station_valid:
                return {"success": False, "message": station_message}
            
            # Получаем соединение
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            
            # Отправляем команду на возврат повербанка
            secret_key = connection.secret_key
            if not secret_key:
                return {"success": False, "message": "Нет секретного ключа для станции"}
            
            # Находим свободный слот для возврата
            free_slot = await self._find_free_slot(station_id)
            if not free_slot:
                return {"success": False, "message": "Нет свободных слотов для возврата"}
            
            # Создаем команду возврата
            return_command = build_return_power_bank(
                secret_key=secret_key,
                slot=free_slot,
                vsn=1
            )
            
            # Отправляем команду станции
            try:
                connection.writer.write(return_command)
                await connection.writer.drain()
                logger.info(f"Команда возврата отправлена на станцию {station_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки команды возврата: {e}")
                return {"success": False, "message": f"Ошибка отправки команды: {e}"}
            
            # Ждем 10 секунд для вставки повербанка пользователем
            logger.info(f"Ожидаем вставку повербанка в течение 10 секунд...")
            await asyncio.sleep(10)
            
            # Запрашиваем инвентарь для получения актуальных данных о вставленном повербанке
            await self._request_inventory_after_operation(station_id)
            
            # Дополнительно ждем еще 2 секунды для обработки ответа инвентаря
            await asyncio.sleep(2)
            
            # Проверяем, был ли повербанк действительно вставлен в станцию
            powerbank_inserted = await self._check_powerbank_insertion(station_id, powerbank_id)
            
            if powerbank_inserted:
                # Обновляем статус заказа на 'return'
                await Order.update_order_status(self.db_pool, order_id, 'return')
                logger.info(f"Заказ {order_id} изменен на статус 'return' - повербанк {powerbank_id} возвращен")
                message = "Повербанк успешно возвращен и обработан станцией."
            else:
                logger.warning(f"Повербанк {powerbank_id} не был обнаружен в станции {station_id} после 10 секунд ожидания")
                message = "Повербанк не был обнаружен в станции. Проверьте, что повербанк вставлен правильно."
            
            logger.info(f"Процесс ручного возврата завершен: order_id={order_id}")
            
            return {
                "success": True,
                "message": message,
                "order_id": order_id,
                "powerbank_id": powerbank_id,
                "station_id": station_id,
                "powerbank_inserted": powerbank_inserted
            }
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка процесса ручного возврата: {e}")
            return {"success": False, "message": f"Ошибка процесса возврата: {e}"}
    
    async def _find_free_slot(self, station_id: int) -> Optional[int]:
        """
        Находит свободный слот в станции для возврата повербанка
        """
        try:
            from models.station_powerbank import StationPowerbank
            
            # Получаем все занятые слоты в станции
            occupied_slots = await StationPowerbank.get_occupied_slots(self.db_pool, station_id)
            
            # Получаем информацию о станции для определения общего количества слотов
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return None
            
            # Используем количество слотов из базы данных
            max_slots = station.slots_declared
            
            # Ищем первый свободный слот
            for slot_number in range(1, max_slots + 1):
                if slot_number not in occupied_slots:
                    logger = get_logger('return_powerbank')
                    logger.info(f"Найден свободный слот {slot_number} для возврата в станции {station_id}")
                    return slot_number
            
            return None
            
        except Exception as e:
            logger = get_logger('return_powerbank')
            logger.error(f"Ошибка поиска свободного слота: {e}")
            return None
