"""
Обработчик команды запроса инвентаря кабинета
"""
import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone

from models.station import Station
from models.powerbank import Powerbank
from utils.packet_utils import build_query_inventory_request, parse_query_inventory_response
from models.connection import StationConnection

class QueryInventoryHandler:
    """Обработчик для команды запроса инвентаря кабинета (0x64)"""

    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Настраивает логгер для записи в файл"""
        os.makedirs('logs', exist_ok=True)
        logger = logging.getLogger('query_inventory')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        handler = logging.FileHandler('logs/query_inventory.log', encoding='utf-8')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

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
        Сохраняет данные в кэш соединения
        """
        try:
            # Парсим ответ
            response = parse_query_inventory_response(data)
            
            if not response.get("CheckSumValid", False):
                print(f" Получен некорректный ответ на запрос инвентаря от станции {connection.box_id}")
                return
            
            # Проверяем токен
            from utils.packet_utils import verify_token
            import struct
            payload = struct.pack("BB", response.get('SlotsNum', 0), response.get('RemainNum', 0))
            # Добавляем данные слотов
            for slot_data in response.get('Slots', []):
                payload += struct.pack("B8sBHHBBB", 
                    slot_data['Slot'],
                    slot_data['TerminalID'].encode('ascii'),
                    slot_data['Level'],
                    slot_data['Voltage'],
                    slot_data['Current'],
                    slot_data['Temperature'],
                    0,  # status byte
                    slot_data['SOH']
                )
            
            received_token = int(response.get("Token", "0x0"), 16)
            if not verify_token(payload, connection.secret_key, received_token):
                print(f"Неверный токен в ответе инвентаря от станции {connection.box_id}")
                return
            
            print(f" Получен ответ на запрос инвентаря от станции {connection.box_id}")
            print(f" Слотов: {response.get('SlotsNum', 0)}, Свободно: {response.get('RemainNum', 0)}")
            print(f" Повербанков в ответе: {len(response.get('Slots', []))}")
            
            # Обновляем remain_num станции в БД
            station = await Station.get_by_id(self.db_pool, connection.station_id)
            if station:
                await station.update_remain_num(self.db_pool, response.get('RemainNum', 0))
                print(f" Обновлен remain_num для станции {station.box_id}: {response.get('RemainNum', 0)}")
            
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
                    # Повербанк существует, обновляем его статус и SOH
                    await powerbank.update_status_and_soh(self.db_pool, 'active', soh)
                    print(f" Обновлен повербанк {terminal_id}: статус 'active', SOH {soh}")
                else:
                    # Повербанк не существует, создаем его
                    new_powerbank = await Powerbank.create(self.db_pool, station.org_unit_id, terminal_id, soh, 'active')
                    if new_powerbank:
                        print(f" Создан новый повербанк {terminal_id} с SOH {soh}")
                    else:
                        print(f" Не удалось создать повербанк для TerminalID {terminal_id}")

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
            
            print(f" Инвентарь станции {connection.box_id} сохранен в кэш: {len(inventory_data)} слотов")
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос инвентаря от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Слотов: {response.get('SlotsNum', 0)}, Свободно: {response.get('RemainNum', 0)}, "
                           f"Повербанков: {len(response.get('Slots', []))}")
            
        except Exception as e:
            print(f" Ошибка обработки ответа на запрос инвентаря: {e}")
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