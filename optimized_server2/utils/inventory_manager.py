"""
Менеджер для работы с инвентарем станций
"""
import asyncio
from typing import Optional, Dict, Any
from models.station_powerbank import StationPowerbank
from utils.packet_utils import build_query_inventory_request, parse_query_inventory_response


class InventoryManager:
    """Менеджер для управления инвентарем станций"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def request_inventory_after_operation(self, station_id: int, connection) -> None:
        """
        Запрашивает инвентарь станции после операции (выдача/возврат/извлечение)
        """
        try:
            if not connection or not connection.secret_key:
                print(f"Нет соединения или ключа для станции {station_id}")
                return
            
            # Создаем запрос инвентаря
            inventory_request = build_query_inventory_request(
                secret_key=connection.secret_key,
                vsn=1,  # Используем VSN=1 по умолчанию
                station_box_id=connection.box_id or f"station_{station_id}"
            )
            
            # Отправляем запрос
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(inventory_request)
                await connection.writer.drain()
                print(f"Запрос инвентаря отправлен станции {station_id}")
                
                # Ждем ответ (с таймаутом)
                await asyncio.sleep(0.5)  # Даем время на ответ
            else:
                print(f"TCP соединение со станцией {station_id} недоступно")
                
        except Exception as e:
            print(f"Ошибка запроса инвентаря для станции {station_id}: {e}")
    
    async def process_inventory_response(self, data: bytes, station_id: int) -> None:
        """
        Обрабатывает ответ на запрос инвентаря и обновляет station_powerbank
        """
        try:
            # Парсим ответ
            inventory_data = parse_query_inventory_response(data)
            
            if inventory_data.get("Error"):
                print(f"Ошибка парсинга инвентаря станции {station_id}: {inventory_data['Error']}")
                return
            
            if not inventory_data.get("CheckSumValid", False):
                print(f"Неверный checksum в ответе инвентаря станции {station_id}")
                return
            
            slots = inventory_data.get("Slots", [])
            if not slots:
                print(f"Нет данных о слотах в ответе инвентаря станции {station_id}")
                return
            
            print(f"Обрабатываем инвентарь станции {station_id}: {len(slots)} слотов")
            
            # Синхронизируем данные с базой
            await self._sync_inventory_with_database(station_id, slots)
            
        except Exception as e:
            print(f"Ошибка обработки инвентаря станции {station_id}: {e}")
    
    async def _sync_inventory_with_database(self, station_id: int, slots: list) -> None:
        """
        Синхронизирует данные инвентаря с таблицей station_powerbank
        """
        try:
            print(f"Начинаем синхронизацию station_powerbank для станции {station_id}")
            
            # Получаем текущие повербанки в станции
            current_powerbanks = await StationPowerbank.get_by_station(self.db_pool, station_id)
            print(f"Получено слотов: {len(current_powerbanks)}")
            
            # Очищаем все старые данные station_powerbank для этой станции
            await StationPowerbank.clear_station_powerbanks(self.db_pool, station_id)
            print(f"Очищены старые данные station_powerbank для станции {station_id}")
            
            # Обрабатываем каждый слот из инвентаря
            added_count = 0
            for slot_data in slots:
                slot_number = slot_data.get('Slot')
                terminal_id = slot_data.get('TerminalID')
                level = slot_data.get('Level')
                voltage = slot_data.get('Voltage')
                temperature = slot_data.get('Temperature')
                status = slot_data.get('Status', {})
                
                # Проверяем, есть ли повербанк в слоте (по статусу InsertionSwitch)
                has_powerbank = status.get('InsertionSwitch', 0) == 1
                
                if has_powerbank and terminal_id and terminal_id != '0000000000000000':
                    # Есть повербанк в слоте - добавляем его
                    success = await self._add_new_powerbank(
                        station_id, slot_number, terminal_id, level, voltage, temperature
                    )
                    if success:
                        added_count += 1
            
            print(f"Синхронизация завершена. Добавлено повербанков: {added_count}")
            
        except Exception as e:
            print(f"Ошибка синхронизации инвентаря станции {station_id}: {e}")
    
    async def _update_existing_powerbank(self, station_id: int, slot_number: int, 
                                       terminal_id: str, level: int, voltage: int, 
                                       temperature: int) -> None:
        """Обновляет существующий повербанк"""
        try:
            # Получаем powerbank_id по terminal_id
            powerbank_id = await self._get_powerbank_id_by_terminal_id(terminal_id)
            if not powerbank_id:
                print(f"Повербанк {terminal_id} не найден в базе")
                return
            
            # Обновляем данные
            await StationPowerbank.update_powerbank_data(
                self.db_pool, station_id, slot_number, level, voltage, temperature
            )
            
            print(f"Обновлен повербанк {terminal_id} в слоте {slot_number} станции {station_id}")
            
        except Exception as e:
            print(f"Ошибка обновления повербанка в слоте {slot_number}: {e}")
    
    async def _add_new_powerbank(self, station_id: int, slot_number: int, 
                               terminal_id: str, level: int, voltage: int, 
                               temperature: int) -> bool:
        """Добавляет новый повербанк"""
        try:
            # Получаем powerbank_id по terminal_id
            powerbank_id = await self._get_powerbank_id_by_terminal_id(terminal_id)
            if not powerbank_id:
                print(f"Повербанк {terminal_id} не найден в базе")
                return False
            
            # Добавляем повербанк
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank_id, slot_number, 
                level, voltage, temperature
            )
            
            print(f"Добавлен повербанк {terminal_id} в слот {slot_number} станции {station_id}")
            return True
            
        except Exception as e:
            print(f"Ошибка добавления повербанка в слот {slot_number}: {e}")
            return False
    
    async def _get_powerbank_id_by_terminal_id(self, terminal_id: str) -> Optional[int]:
        """Получает ID повербанка по terminal_id"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id FROM powerbank WHERE serial_number = %s
                    """, (terminal_id,))
                    result = await cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            print(f"Ошибка поиска повербанка {terminal_id}: {e}")
            return None
