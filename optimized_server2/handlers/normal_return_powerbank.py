"""
Обработчик для обычного возврата повербанков (без ошибки)
"""
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

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
    
    async def _send_inventory_request_silently(self, station_id: int) -> None:
        """
        Отправляет запрос инвентаризации без логирования в фоновом режиме
        """
        try:
            from utils.packet_utils import build_query_inventory_request
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection or not connection.writer or connection.writer.is_closing():
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
            
            connection.writer.write(inventory_request_packet)
            await connection.writer.drain()
            
        except Exception:
            # Игнорируем ошибки (без логирования)
            pass

    async def handle_powerbank_insertion(self, station_id: int, slot_number: int, powerbank_id: int) -> Dict[str, Any]:
        """
        Обрабатывает вставку повербанка в станцию (обычный возврат без ошибки)
        """
        try:
            # Получаем повербанк
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "error": "Повербанк не найден"}
            
            # Получаем станцию для проверки совместимости групп
            from models.station import Station
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "error": "Станция не найдена"}
            
            # Проверяем совместимость групп повербанка и станции
            if powerbank.org_unit_id and station.org_unit_id:
                from utils.org_unit_utils import is_powerbank_compatible, get_compatibility_reason
                
                compatible = await is_powerbank_compatible(
                    self.db_pool, powerbank.org_unit_id, station.org_unit_id
                )
                
                if not compatible:
                    reason = await get_compatibility_reason(
                        self.db_pool, powerbank.org_unit_id, station.org_unit_id
                    )
                    return {
                        "success": False, 
                        "error": f"Повербанк нельзя вернуть в эту станцию. {reason}"
                    }
                else:
                    reason = await get_compatibility_reason(
                        self.db_pool, powerbank.org_unit_id, station.org_unit_id
                    )

            # Проверяем, есть ли активный заказ на выдачу для этого повербанка
            active_order = await Order.get_active_borrow_order(self.db_pool, powerbank.serial_number)
            
            if active_order:
                # Закрываем активный заказ
                await active_order.update_status(self.db_pool, 'return')
                
                # Получаем user_id по телефону
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT user_id FROM app_user WHERE phone_e164 = %s", 
                            (active_order.user_phone,)
                        )
                        user_result = await cur.fetchone()
                        user_id = user_result[0] if user_result else None
                
                # Логируем действие
                await ActionLog.create(
                    self.db_pool,
                    user_id=user_id,
                    action_type='order_update',
                    entity_type='order',
                    entity_id=active_order.order_id,
                    description='Обычный возврат повербанка'
                )
                
                # Отправляем WebSocket уведомление о возврате
                if user_id:
                    try:
                        from utils.user_notification_manager import user_notification_manager
                        notification_sent = await user_notification_manager.send_powerbank_return_notification(
                            user_id=user_id,
                            order_id=active_order.order_id,
                            powerbank_serial=powerbank.serial_number,
                            message='Спасибо за возврат! Заказ успешно закрыт.'
                        )
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки WebSocket уведомления о возврате: {e}")

            # Обновляем статус повербанка на активный (если он был в другом статусе)
            if powerbank.status != 'active':
                await powerbank.update_status(self.db_pool, 'active')

            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(self.db_pool, station_id, powerbank_id, slot_number)
            
            # Обновляем remain_num станции (объект station уже получен ранее)
            # При возврате повербанков становится больше → remain_num увеличивается
            new_remain_num = int(station.remain_num) + 1
            await station.update_remain_num(self.db_pool, new_remain_num)

            result = {
                "success": True,
                "message": "Спасибо за возврат! Заказ закрыт.",
                "notification": "Спасибо за возврат! Заказ успешно закрыт.",
                "powerbank_id": powerbank_id,
                "station_id": station_id,
                "slot_number": slot_number,
                "order_closed": active_order is not None,
                "order_id": active_order.order_id if active_order else None
            }
            
            # Отправляем запрос инвентаризации в фоне без логирования
            asyncio.create_task(self._send_inventory_request_silently(station_id))
            
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
            # Получаем повербанк для получения его serial_number
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "error": "Повербанк не найден"}
            
            # Проверяем, есть ли активный заказ на выдачу для этого повербанка
            active_order = await Order.get_active_borrow_order(self.db_pool, powerbank.serial_number)
            
            if active_order:
                # Закрываем активный заказ
                await active_order.update_status(self.db_pool, 'return')
                
                # Получаем user_id по телефону
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT user_id FROM app_user WHERE phone_e164 = %s", 
                            (active_order.user_phone,)
                        )
                        user_result = await cur.fetchone()
                        user_id = user_result[0] if user_result else None
                
                # Логируем действие
                await ActionLog.create(
                    self.db_pool,
                    user_id=user_id,
                    action_type='order_update',
                    entity_type='order',
                    entity_id=active_order.order_id,
                    description='Возврат повербанка (обнаружен в инвентаре)'
                )
                
                # Отправляем WebSocket уведомление о возврате
                if user_id:
                    try:
                        from utils.user_notification_manager import user_notification_manager
                        notification_sent = await user_notification_manager.send_powerbank_return_notification(
                            user_id=user_id,
                            order_id=active_order.order_id,
                            powerbank_serial=powerbank.serial_number,
                            message='Спасибо за возврат! Заказ успешно закрыт.'
                        )
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки WebSocket уведомления о возврате: {e}")
                
                return {
                    "success": True,
                    "message": "Спасибо за возврат! Заказ закрыт.",
                    "notification": "Спасибо за возврат! Заказ успешно закрыт.",
                    "order_id": active_order.order_id,
                    "user_phone": active_order.user_phone
                }
            else:
                return {
                    "success": True,
                    "message": "Повербанк обнаружен в инвентаре, но нет активного заказа",
                    "order_id": None
                }

        except Exception as e:
            self.logger.error(f"Ошибка обработки возврата из инвентаря: {e}")
            return {"success": False, "error": f"Ошибка обработки: {str(e)}"}
