"""
Обработчик для принудительного извлечения повербанков
"""
from typing import Optional
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from utils.packet_utils import build_force_eject_request


class EjectPowerbankHandler:
    """Обработчик для принудительного извлечения повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_force_eject_request(self, station_id: int, slot_number: int, 
                                       connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на принудительное извлечение повербанка
        Возвращает команду для отправки на станцию или None
        """
        try:
            # Проверяем, есть ли повербанк в указанном слоте
            station_powerbank = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, slot_number
            )
            
            if not station_powerbank:
                print(f"В слоте {slot_number} станции {station_id} нет повербанка для извлечения")
                return None
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для команды извлечения")
                return None
            
            # Создаем команду на принудительное извлечение
            eject_command = build_force_eject_request(
                secret_key=secret_key,
                slot=slot_number,
                vsn=1  # Можно получить из соединения
            )
            
            print(f"Создана команда на принудительное извлечение повербанка из слота {slot_number}")
            return eject_command
            
        except Exception as e:
            print(f"Ошибка обработки запроса на извлечение: {e}")
            return None
    
    async def handle_force_eject_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ от станции на принудительное извлечение
        """
        try:
            # Парсим ответ от станции
            from utils.packet_utils import parse_force_eject_response
            eject_response = parse_force_eject_response(data)
            print(f"Обработан ответ на принудительное извлечение: {eject_response}")
            
            station_id = connection.station_id
            if not station_id:
                return
            
            # Если извлечение успешно, удаляем повербанк из station_powerbank
            if eject_response.get("Success", False):
                # Очищаем все повербанки из станции (принудительное извлечение)
                from models.station_powerbank import StationPowerbank
                removed_count = await StationPowerbank.clear_station_powerbanks(self.db_pool, station_id)
                
                if removed_count > 0:
                    # Обновляем last_seen станции и remain_num
                    from models.station import Station
                    station = await Station.get_by_id(self.db_pool, station_id)
                    if station:
                        await station.update_last_seen(self.db_pool)
                        # Увеличиваем remain_num на количество извлеченных повербанков
                        await station.update_remain_num(self.db_pool, int(station.remain_num) + removed_count)
                    
                    print(f"Успешно извлечено {removed_count} повербанков из станции {station_id}")
                    
                    # Автоматически запрашиваем инвентарь после успешного извлечения
                    await self._request_inventory_after_operation(station_id)
                else:
                    print(f"Не найдены повербанки в станции {station_id} для извлечения")
            
        except Exception as e:
            print(f"Ошибка обработки ответа на извлечение: {e}")
    
    async def process_successful_eject(self, station_id: int, slot_number: int, 
                                     terminal_id: str = None) -> None:
        """
        Обрабатывает успешное извлечение повербанка
        Удаляет повербанк из station_powerbank
        """
        try:
            success = await StationPowerbank.remove_powerbank(
                self.db_pool, station_id, slot_number
            )
            
            if success:
                # Обновляем last_seen станции и remain_num
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    # Увеличиваем remain_num при извлечении
                    await station.update_remain_num(self.db_pool, int(station.remain_num) + 1)
                
                print(f"Повербанк успешно извлечен из слота {slot_number} станции {station_id} и данные обновлены в БД")
            else:
                print(f"Не удалось удалить повербанк из слота {slot_number}")
                
        except Exception as e:
            print(f"Ошибка при удалении повербанка из станции: {e}")
    
    async def extract_incompatible_powerbank(self, station_id: int, slot_number: int, 
                                           terminal_id: str, connection) -> None:
        """
        Извлекает несовместимый повербанк из станции
        """
        try:
            # Отправляем команду на извлечение
            eject_command = await self.handle_force_eject_request(
                station_id, slot_number, connection
            )
            
            if eject_command:
                # Здесь нужно отправить команду на станцию
                # writer.write(eject_command)
                # await writer.drain()
                print(f"Отправлена команда на извлечение несовместимого повербанка {terminal_id}")
            else:
                print(f"Не удалось создать команду на извлечение повербанка {terminal_id}")
                
        except Exception as e:
            print(f"Ошибка при извлечении несовместимого повербанка: {e}")
    
    async def check_and_extract_incompatible_powerbanks(self, station_id: int, 
                                                      connection) -> None:
        """
        Проверяет и извлекает все несовместимые повербанки из станции
        """
        try:
            # Получаем все повербанки в станции
            station_powerbanks = await StationPowerbank.get_by_station(
                self.db_pool, station_id
            )
            
            # Получаем информацию о станции
            station_info = await self._get_station_info(station_id)
            if not station_info:
                return
            
            station_org_unit_id = station_info['org_unit_id']
            
            for sp in station_powerbanks:
                # Получаем информацию о повербанке
                powerbank = await Powerbank.get_by_serial(
                    self.db_pool, sp.powerbank_id
                )
                
                if powerbank and powerbank.org_unit_id != station_org_unit_id:
                    print(f"Найден несовместимый повербанк в слоте {sp.slot_number}")
                    
                    # Извлекаем несовместимый повербанк
                    await self.extract_incompatible_powerbank(
                        station_id, sp.slot_number, powerbank.serial_number, connection
                    )
                    
        except Exception as e:
            print(f"Ошибка при проверке совместимости повербанков: {e}")
    
    async def _get_station_info(self, station_id: int) -> Optional[dict]:
        """Получает информацию о станции"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT station_id, org_unit_id FROM station WHERE station_id = %s
                    """, (station_id,))
                    result = await cur.fetchone()
                    
                    if result:
                        return {
                            'station_id': result[0],
                            'org_unit_id': result[1]
                        }
                    return None
        except Exception as e:
            print(f"Ошибка получения информации о станции: {e}")
            return None
    
    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции с повербанком
        """
        try:
            from handlers.query_inventory import QueryInventoryHandler
            inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            result = await inventory_handler.send_inventory_request(station_id)
            if result["success"]:
                print(f"📦 Запрос инвентаря отправлен после операции извлечения")
            else:
                print(f"❌ Ошибка отправки запроса инвентаря: {result['message']}")
        except Exception as e:
            print(f"❌ Ошибка запроса инвентаря после операции: {e}")
