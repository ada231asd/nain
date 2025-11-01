"""
Обработчик команды запроса инвентаря кабинета
"""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from utils.centralized_logger import get_logger
from models.station import Station
from models.powerbank import Powerbank
from utils.packet_utils import build_query_inventory_request, parse_query_inventory_response, get_moscow_time
from models.connection import StationConnection

class QueryInventoryHandler:
    """Обработчик для команды запроса инвентаря кабинета (0x64)"""

    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('queryinventoryhandler')

    async def send_inventory_request(self, station_id: int) -> Dict[str, Any]:
        """
        Отправляет запрос на получение инвентаря станции.
        """
        station = await Station.get_by_id(self.db_pool, station_id)
        if not station:
            self.logger.error(f"Станция с ID {station_id} не найдена для запроса инвентаря.")
            return {"success": False, "message": "Станция не найдена."}

        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if not connection or not connection.writer or connection.writer.is_closing():
            self.logger.error(f"Соединение со станцией {station.box_id} (ID: {station_id}) неактивно для запроса инвентаря.")
            return {"success": False, "message": "Станция не подключена или соединение неактивно."}

        secret_key = connection.secret_key
        if not secret_key:
            self.logger.error(f"Секретный ключ для станции {station.box_id} (ID: {station_id}) не найден.")
            return {"success": False, "message": "Секретный ключ не найден."}

        try:
            inventory_request_packet = build_query_inventory_request(secret_key, station_box_id=station.box_id)
            packet_hex = inventory_request_packet.hex()

            connection.writer.write(inventory_request_packet)
            await connection.writer.drain()

            return {
                "success": True,
                "message": f"Запрос инвентаря отправлен на станцию {station.box_id}."
            }
        except Exception as e:
            self.logger.error(f"Ошибка отправки запроса инвентаря на станцию {station.box_id} (ID: {station_id}): {e}")
            return {"success": False, "message": f"Ошибка отправки запроса инвентаря: {e}"}

    async def handle_inventory_response(self, data: bytes, connection: StationConnection) -> None:
        """
        Обрабатывает ответ на запрос инвентаря от станции
        """
        try:
            # Парсим ответ
            response = parse_query_inventory_response(data)
            
            if not response.get("CheckSumValid", False):
                return
            
            # Обновляем remain_num станции в БД
            station = await Station.get_by_id(self.db_pool, connection.station_id)
            if station:
                await station.update_remain_num(self.db_pool, response.get('RemainNum', 0))
            
            # Используем InventoryManager для обновления station_powerbank
            from utils.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(self.db_pool)
            await inventory_manager.process_inventory_response(data, connection.station_id)
            
            # Обрабатываем каждый слот из ответа
            inventory_data = []
            for slot_data in response.get('Slots', []):
                slot_number = slot_data['Slot']
                terminal_id = slot_data['TerminalID']
                level = slot_data['Level']
                voltage = slot_data['Voltage']
                current = slot_data['Current']
                temperature = slot_data['Temperature']
                soh = slot_data['SOH']
                status = slot_data['Status']
                
                
                # Проверяем, существует ли повербанк в таблице powerbank
                powerbank = await Powerbank.get_by_serial(self.db_pool, terminal_id)

                if powerbank:
                    
                    try:
                        from models.order import Order
                        active_order = await Order.get_active_borrow_order(self.db_pool, powerbank.powerbank_id)
                    except Exception:
                        active_order = None

                    if active_order:
                        from handlers.normal_return_powerbank import NormalReturnPowerbankHandler
                        normal_return_handler = NormalReturnPowerbankHandler(self.db_pool, self.connection_manager)
                        result = await normal_return_handler.process_inventory_return(powerbank.powerbank_id)

                    
                    # Обновляем SOH
                    soh_int = int(soh) if soh is not None else 0
                    await powerbank.update_soh(self.db_pool, soh_int)
                else:

                    pass

                # Добавляем данные слота в инвентарь
                inventory_data.append({
                    'slot_number': slot_number,
                    'terminal_id': terminal_id,
                    'level': level,
                    'voltage': voltage,
                    'current': current,
                    'temperature': temperature,
                    'soh': soh,
                    'status': status
                })

      
            connection.inventory_cache = {
                'slots_num': response.get('SlotsNum', 0),
                'remain_num': response.get('RemainNum', 0),
                'inventory': inventory_data,
                'last_update': get_moscow_time().isoformat()
            }
            
            # Проверяем и извлекаем несовместимые повербанки после обработки инвентаря
            await self._check_and_extract_incompatible_powerbanks(connection.station_id)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки ответа на запрос инвентаря от станции {connection.box_id}: {e}")

    async def _check_and_extract_incompatible_powerbanks(self, station_id: int) -> None:
        """Проверяет и извлекает несовместимые повербанки после обработки инвентаря"""
        try:
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return
            
            # Используем обработчик извлечения для проверки совместимости
            from handlers.eject_powerbank import EjectPowerbankHandler
            eject_handler = EjectPowerbankHandler(self.db_pool, self.connection_manager)
            await eject_handler.check_and_extract_incompatible_powerbanks(station_id, connection)
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки совместимости повербанков: {e}")

    async def get_station_inventory(self, station_id: int) -> dict:
        """
        Получает инвентарь станции из кэша соединения
        """
        try:
            # Получаем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {
                    "success": False,
                    "error": "Станция не подключена"
                }
            
            # Проверяем, есть ли кэш инвентаря
            if hasattr(connection, 'inventory_cache') and connection.inventory_cache:
                return {
                    "success": True,
                    "inventory": connection.inventory_cache
                }
            else:
                return {
                    "success": False,
                    "error": "Инвентарь не загружен. Отправьте запрос инвентаря."
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка получения инвентаря: {str(e)}"
            }
