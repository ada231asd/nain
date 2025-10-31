"""
Менеджер для работы с инвентарем станций
"""
import asyncio
from typing import Optional, Dict, Any
from models.station_powerbank import StationPowerbank
from utils.packet_utils import build_query_inventory_request, parse_query_inventory_response
from utils.centralized_logger import get_logger


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
                logger = get_logger('inventory_manager'); logger.warning(f"Нет соединения или ключа для станции {station_id}")
                return
            
            # Создаем запрос инвентаря
            inventory_request = build_query_inventory_request(
                secret_key=connection.secret_key,
                vsn=2,  
                station_box_id=connection.box_id or f"station_{station_id}"
            )
            
            # Отправляем запрос
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(inventory_request)
                await connection.writer.drain()
                
                # Ждем ответ
                await asyncio.sleep(0.5)
            else:
                logger = get_logger('inventory_manager'); logger.warning(f"TCP соединение со станцией {station_id} недоступно")
                
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
    
    async def process_inventory_response(self, data: bytes, station_id: int) -> None:
        """
        Обрабатывает ответ на запрос инвентаря и обновляет station_powerbank
        """
        try:
            # Парсим ответ
            inventory_data = parse_query_inventory_response(data)
            
            if inventory_data.get("Error"):
                logger = get_logger('inventory_manager')
                logger.error(f"Ошибка: {e}")
                return
            
            if not inventory_data.get("CheckSumValid", False):
                logger = get_logger('inventory_manager'); logger.warning(f"Неверный checksum в ответе инвентаря станции {station_id}")
                return
            
            slots = inventory_data.get("Slots", [])
            
            # Синхронизируем данные с базой
            await self._sync_inventory_with_database(station_id, slots)
            
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
    
    async def _sync_inventory_with_database(self, station_id: int, slots: list) -> None:
        """
        Синхронизирует данные инвентаря с таблицей station_powerbank, обновляя ТОЛЬКО изменения.

        """
        try:
            logger = get_logger('inventory_manager')
            # Текущее состояние БД по слотам
            current_records = await StationPowerbank.get_by_station(self.db_pool, station_id)
            current_by_slot = {rec.slot_number: rec for rec in current_records}

            # Построим целевое состояние по слотам из ответа станции
            target_by_slot = {}

            changes_applied = 0
            unchanged = 0

            for slot_data in slots:
                slot_number = slot_data.get('Slot')
                terminal_id = slot_data.get('TerminalID')
                level = slot_data.get('Level')
                voltage = slot_data.get('Voltage')
                temperature = slot_data.get('Temperature')
                status = slot_data.get('Status', {})

                has_powerbank = status.get('InsertionSwitch', 0) == 1

                if has_powerbank and terminal_id and terminal_id != '0000000000000000':
                    # Разрешаем только валидные повербанки
                    powerbank_id = await self._get_powerbank_id_by_terminal_id(terminal_id)
                    if not powerbank_id:
                        
                        created = await self._create_and_add_unknown_powerbank(
                            station_id, slot_number, terminal_id, level, voltage, temperature
                        )
                        if created:
                  
                            powerbank_id = await self._get_powerbank_id_by_terminal_id(terminal_id)
                    if not powerbank_id:
                        continue

                    target_by_slot[slot_number] = {
                        'powerbank_id': powerbank_id,
                        'level': int(level) if level is not None else None,
                        'voltage': int(voltage) if voltage is not None else None,
                        'temperature': int(temperature) if temperature is not None else None
                    }

                    existing = current_by_slot.get(slot_number)
                    if existing:
                        same_pb = existing.powerbank_id == powerbank_id
                        same_level = (existing.level == target_by_slot[slot_number]['level'])
                        same_voltage = (existing.voltage == target_by_slot[slot_number]['voltage'])
                        same_temperature = (existing.temperature == target_by_slot[slot_number]['temperature'])
                        if same_pb and same_level and same_voltage and same_temperature:
                            unchanged += 1
                        else:
                            await StationPowerbank.add_powerbank(
                                self.db_pool,
                                station_id,
                                powerbank_id,
                                slot_number,
                                target_by_slot[slot_number]['level'],
                                target_by_slot[slot_number]['voltage'],
                                target_by_slot[slot_number]['temperature']
                            )
                            changes_applied += 1
                    else:
                        await StationPowerbank.add_powerbank(
                            self.db_pool,
                            station_id,
                            powerbank_id,
                            slot_number,
                            target_by_slot[slot_number]['level'],
                            target_by_slot[slot_number]['voltage'],
                            target_by_slot[slot_number]['temperature']
                        )
                        changes_applied += 1

            removed = 0
            for slot_number, existing in current_by_slot.items():
                if slot_number not in target_by_slot:
                    deleted = await StationPowerbank.remove_powerbank(self.db_pool, station_id, slot_number)
                    if deleted:
                        removed += 1

        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
    
    async def _update_existing_powerbank(self, station_id: int, slot_number: int, 
                                       terminal_id: str, level: int, voltage: int, 
                                       temperature: int) -> None:
        """Обновляет существующий повербанк"""
        try:
            # Получаем powerbank_id по terminal_id
            powerbank_id = await self._get_powerbank_id_by_terminal_id(terminal_id)
            if not powerbank_id:
                logger = get_logger('inventory_manager'); logger.info(f"Повербанк {terminal_id} не найден в базе")
                return
            
            # Обновляем данные
            await StationPowerbank.update_powerbank_data(
                self.db_pool, station_id, slot_number, level, voltage, temperature
            )
            
            logger = get_logger('inventory_manager'); logger.info(f"Обновлен повербанк {terminal_id} в слоте {slot_number} станции {station_id}")
            
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
    
    async def _add_existing_powerbank(self, station_id: int, slot_number: int, 
                                    powerbank_id: int, level: int, voltage: int, 
                                    temperature: int) -> bool:
        """Добавляет существующий повербанк в станцию"""
        try:
            # Добавляем повербанк
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank_id, slot_number, 
                level, voltage, temperature
            )
            
            logger = get_logger('inventory_manager')
            logger.info(f"Добавлен существующий повербанк {powerbank_id} в слот {slot_number} станции {station_id}")
            
            try:
                import sys
                return_handler = None
                
                # Ищем обработчик в модулях
                for module_name, module in sys.modules.items():
                    if hasattr(module, 'shared_return_handler'):
                        return_handler = getattr(module, 'shared_return_handler')
                        break
                
                if return_handler:
                    result = await return_handler.handle_powerbank_insertion(station_id, slot_number, powerbank_id)
                    
                    if result.get('success'):
                        logger.info(f"Обработан возврат с ошибкой: {result.get('message', '')}")
                    else:
                        logger.debug(f"Нет ожидающих возврат пользователей для повербанка {powerbank_id}: {result.get('error', '')}")
                else:
                    logger.debug("Обработчик возврата не найден, пропускаем проверку")
                    
            except Exception as return_error:
                logger.warning(f"Ошибка проверки возврата с ошибкой: {return_error}")
            
            return True
            
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
            return False
    
    async def _create_and_add_unknown_powerbank(self, station_id: int, slot_number: int, 
                                              terminal_id: str, level: int, voltage: int, 
                                              temperature: int) -> bool:
        """Создает новый повербанк со статусом 'unknown' и добавляет в станцию"""
        try:
            from models.powerbank import Powerbank
            from models.station import Station
            
            # Получаем информацию о станции
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                logger = get_logger('inventory_manager')
                logger.error(f"Станция {station_id} не найдена")
                return False
            
            # Создаем повербанк со статусом 'unknown' в группе станции
            new_powerbank = await Powerbank.create_unknown(
                self.db_pool, 
                terminal_id, 
                station.org_unit_id
            )
            
            if not new_powerbank:
                logger = get_logger('inventory_manager')
                logger.error(f"Не удалось создать повербанк {terminal_id}")
                return False
            
            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, new_powerbank.powerbank_id, slot_number, 
                level, voltage, temperature
            )
            
            logger = get_logger('inventory_manager')
            logger.info(f"Создан новый повербанк {terminal_id} со статусом 'unknown' и добавлен в слот {slot_number} станции {station_id}")
            return True
            
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
            return False
    
    async def _get_powerbank_id_by_terminal_id(self, terminal_id: str) -> Optional[int]:
        """Получает ID повербанка по terminal_id"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id FROM powerbank WHERE serial_number COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
                    """, (terminal_id,))
                    result = await cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger = get_logger('inventory_manager')
            logger.error(f"Ошибка: {e}")
            return None
