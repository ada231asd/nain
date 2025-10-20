"""
Обработчик для обычного возврата повербанков (без ошибки)
"""
from typing import Optional, Dict, Any
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from models.action_log import ActionLog
from utils.centralized_logger import get_logger
from utils.time_utils import get_moscow_time


class NormalReturnPowerbankHandler:
    """Обработчик для обычного возврата повербанков (без ошибки)"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('normal_return_powerbank')

    async def handle_powerbank_insertion(self, station_id: int, slot_number: int, powerbank_id: int) -> Dict[str, Any]:
        """
        Обрабатывает вставку повербанка в станцию (обычный возврат без ошибки)
        """
        try:
            self.logger.info(f"Обработка обычного возврата повербанка {powerbank_id} в станцию {station_id}, слот {slot_number}")
            
            # Получаем повербанк
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "error": "Повербанк не найден"}

            # Проверяем, есть ли активный заказ на выдачу для этого повербанка
            active_order = await Order.get_active_borrow_order(self.db_pool, powerbank_id)
            
            if active_order:
                # Закрываем активный заказ
                await active_order.update_status(self.db_pool, 'return')
                self.logger.info(f"Активный заказ {active_order.order_id} закрыт для повербанка {powerbank_id}")
                
                # Логируем действие
                await ActionLog.create(
                    self.db_pool,
                    user_id=active_order.user_id,
                    action_type='order_update',
                    entity_type='order',
                    entity_id=active_order.order_id,
                    description='Обычный возврат повербанка'
                )
            else:
                self.logger.info(f"Нет активного заказа для повербанка {powerbank_id}")

            # Обновляем статус повербанка на активный (если он был в другом статусе)
            if powerbank.status != 'active':
                await powerbank.update_status(self.db_pool, 'active')
                self.logger.info(f"Статус повербанка {powerbank_id} обновлен на 'active'")

            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(self.db_pool, station_id, powerbank_id, slot_number)
            
            # Обновляем remain_num станции
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if station:
                # Уменьшаем remain_num при возврате (повербанк занял слот)
                new_remain_num = max(0, int(station.remain_num) - 1)
                await station.update_remain_num(self.db_pool, new_remain_num)
                self.logger.info(f"Обновлен remain_num станции {station_id}: {new_remain_num}")

            result = {
                "success": True,
                "message": "Повербанк успешно возвращен",
                "powerbank_id": powerbank_id,
                "station_id": station_id,
                "slot_number": slot_number,
                "order_closed": active_order is not None,
                "order_id": active_order.order_id if active_order else None
            }

            self.logger.info(f"Обычный возврат повербанка {powerbank_id} успешно обработан")
            return result

        except Exception as e:
            self.logger.error(f"Ошибка обработки обычного возврата повербанка: {e}")
            return {"success": False, "error": f"Ошибка обработки: {str(e)}"}

    async def handle_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на возврат повербанка от станции (команда 0x66) - только обычный возврат
        """
        try:
            from utils.packet_utils import parse_return_power_bank_request, build_return_power_bank_response
            from utils.station_resolver import get_station_id_by_box_id
            
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
            
            self.logger.info(f"Получен запрос на обычный возврат повербанка: слот {slot}, terminal_id {terminal_id}")

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
            
            # Обрабатываем обычный возврат
            powerbank_id = powerbank.powerbank_id
            result = await self.handle_powerbank_insertion(station_id, slot, powerbank_id)
            
            if result.get('success'):
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
                    vsn=vsn,
                    token=connection.token
                )
            else:
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
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки запроса обычного возврата: {e}")
            return None

    async def process_inventory_return(self, powerbank_id: int) -> Dict[str, Any]:
        """
        Обрабатывает возврат повербанка, обнаруженного в инвентаре станции
        """
        try:
            # Проверяем, есть ли активный заказ на выдачу для этого повербанка
            active_order = await Order.get_active_borrow_order(self.db_pool, powerbank_id)
            
            if active_order:
                # Закрываем активный заказ
                await active_order.update_status(self.db_pool, 'return')
                self.logger.info(f"Активный заказ {active_order.order_id} закрыт для повербанка {powerbank_id} (обнаружен в инвентаре)")
                
                # Логируем действие
                await ActionLog.create(
                    self.db_pool,
                    user_id=active_order.user_id,
                    action_type='order_update',
                    entity_type='order',
                    entity_id=active_order.order_id,
                    description='Возврат повербанка (обнаружен в инвентаре)'
                )
                
                return {
                    "success": True,
                    "message": "Заказ закрыт (повербанк обнаружен в инвентаре)",
                    "order_id": active_order.order_id,
                    "user_id": active_order.user_id
                }
            else:
                self.logger.info(f"Нет активного заказа для повербанка {powerbank_id} (обнаружен в инвентаре)")
                return {
                    "success": True,
                    "message": "Повербанк обнаружен в инвентаре, но нет активного заказа",
                    "order_id": None
                }

        except Exception as e:
            self.logger.error(f"Ошибка обработки возврата из инвентаря: {e}")
            return {"success": False, "error": f"Ошибка обработки: {str(e)}"}
