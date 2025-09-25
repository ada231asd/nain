"""
Обработчик команды запроса инвентаря кабинета
"""
from typing import Dict, Any
from datetime import datetime, timezone

from utils.centralized_logger import get_logger
from models.station import Station
from models.powerbank import Powerbank
from utils.packet_utils import build_query_inventory_request, parse_query_inventory_response
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

            self.logger.info(f"Запрос инвентаря отправлен на станцию {station.box_id} (ID: {station_id}) | Пакет: {packet_hex}")
            print(f" Запрос инвентаря отправлен на станцию {station.box_id} (ID: {station_id})")

            return {
                "success": True,
                "message": f"Запрос инвентаря отправлен на станцию {station.box_id}.",
                "packet_hex": packet_hex
            }
        except Exception as e:
            self.logger.error(f"Ошибка отправки запроса инвентаря на станцию {station.box_id} (ID: {station_id}): {e}")
            return {"success": False, "message": f"Ошибка отправки запроса инвентаря: {e}"}

    async def handle_inventory_response(self, data: bytes, connection: StationConnection) -> None:
        """
        Обрабатывает ответ на запрос инвентаря от станции
        Сохраняет данные в кэш соединения и обновляет station_powerbank
        """
        try:
            # Парсим ответ
            response = parse_query_inventory_response(data)
            
            if not response.get("CheckSumValid", False):
                print(f"❌ Получен некорректный ответ на запрос инвентаря от станции {connection.box_id}")
                return
            
            print(f"📦 Получен ответ на запрос инвентаря от станции {connection.box_id}")
            print(f"   Слотов: {response.get('SlotsNum', 0)}, Свободно: {response.get('RemainNum', 0)}")
            print(f"   Повербанков в ответе: {len(response.get('Slots', []))}")
            
            # Обновляем remain_num станции в БД
            station = await Station.get_by_id(self.db_pool, connection.station_id)
            if station:
                await station.update_remain_num(self.db_pool, response.get('RemainNum', 0))
                print(f"   Обновлен remain_num для станции {station.box_id}: {response.get('RemainNum', 0)}")
            
            # Используем InventoryManager для обновления station_powerbank
            from utils.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(self.db_pool)
            await inventory_manager.process_inventory_response(data, connection.station_id)
            
            # Обрабатываем каждый слот из ответа для кэша
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
                    # Повербанк существует, обновляем его статус и SOH
                    await powerbank.update_status_and_soh(self.db_pool, 'active', soh)
                    print(f"📱 Обновлен повербанк {terminal_id}: статус 'active', SOH {soh}")
                else:
                    # Повербанк не существует, создаем его
                    new_powerbank = await Powerbank.create(self.db_pool, station.org_unit_id, terminal_id, soh, 'active')
                    if new_powerbank:
                        print(f"📱 Создан новый повербанк {terminal_id} с SOH {soh}")
                    else:
                        print(f"❌ Не удалось создать повербанк для TerminalID {terminal_id}")

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

            # Сохраняем инвентарь в кэш соединения
            connection.inventory_cache = {
                'slots_num': response.get('SlotsNum', 0),
                'remain_num': response.get('RemainNum', 0),
                'inventory': inventory_data,
                'last_update': datetime.now(timezone.utc).isoformat()
            }
            
            print(f"✅ Инвентарь станции {connection.box_id} сохранен в кэш: {len(inventory_data)} слотов")
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос инвентаря от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Слотов: {response.get('SlotsNum', 0)}, Свободно: {response.get('RemainNum', 0)}, "
                           f"Повербанков: {len(response.get('Slots', []))}")
            
        except Exception as e:
            print(f"❌ Ошибка обработки ответа на запрос инвентаря: {e}")
            self.logger.error(f"Ошибка обработки ответа на запрос инвентаря от станции {connection.box_id}: {e}")

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