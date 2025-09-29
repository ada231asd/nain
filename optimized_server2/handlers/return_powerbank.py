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
                
                # Автоматически запрашиваем инвентарь после возврата
                # Инвентарь сам определит, какой повербанк вставлен и обновит БД
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