"""
Обработчик для возврата повербанков
"""
from typing import Optional, Dict, Any
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from utils.packet_utils import build_return_power_bank_response, parse_return_power_bank_request


class ReturnPowerbankHandler:
    """Обработчик для возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на возврат повербанка
        Возвращает ответный пакет или None
        """
        try:
            # Парсим запрос на возврат
            return_request = parse_return_power_bank_request(data)
            print(f"Принят Return Power Bank Request: {return_request}")
            
            station_id = connection.station_id
            if not station_id:
                print("Станция не найдена для соединения")
                return self._build_error_response(return_request)
            
            # Получаем данные из запроса
            slot = return_request.get("Slot")
            terminal_id = return_request.get("TerminalID")
            level = return_request.get("Level")
            voltage = return_request.get("Voltage")
            current = return_request.get("Current")
            temperature = return_request.get("Temperature")
            status = return_request.get("Status")
            soh = return_request.get("SOH")
            vsn = return_request.get("VSN")
            token = int(return_request.get("Token", "0x0"), 16)
            
            # Проверяем, существует ли повербанк в БД
            powerbank = await Powerbank.get_by_serial(self.db_pool, terminal_id)
            
            if not powerbank:
                print(f"Повербанк {terminal_id} не найден в БД")
                # Отправляем ответ с ошибкой - повербанк не найден
                return self._build_error_response(return_request, result=4)  # Invalid Power Bank ID
            
            # Проверяем совместимость групп с учетом иерархии
            station = await self._get_station_info(station_id)
            if not station:
                return self._build_error_response(return_request, result=0)  # Failure
            
            # Проверяем совместимость повербанка и станции
            is_compatible = await self._check_powerbank_station_compatibility(
                powerbank.org_unit_id, station['org_unit_id']
            )
            
            if not is_compatible:
                print(f"Повербанк {terminal_id} несовместим с группой станции - принудительная выдача")
                # Отправляем команду принудительной выдачи
                await self._send_force_eject_command(station_id, slot, connection)
                return self._build_error_response(return_request, result=2)  # Power Bank Status Error
            
            # Проверяем статус повербанка - принимаем только активные
            if powerbank.status != 'active':
                print(f"Повербанк {terminal_id} имеет статус {powerbank.status} - возврат отклонен")
                return self._build_error_response(return_request, result=2)  # Power Bank Status Error
            
            # Проверяем, не занят ли слот
            existing_powerbank = await StationPowerbank.get_by_slot(self.db_pool, station_id, slot)
            if existing_powerbank:
                print(f"Слот {slot} уже занят повербанком {existing_powerbank.powerbank_id}")
                return self._build_error_response(return_request, result=5)  # Slot not empty
            
            # Добавляем повербанк в станцию
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank.powerbank_id, slot,
                level, voltage, temperature
            )
            
            # Обновляем last_seen станции и remain_num
            from models.station import Station
            station_obj = await Station.get_by_id(self.db_pool, station_id)
            if station_obj:
                await station_obj.update_last_seen(self.db_pool)
                # Уменьшаем remain_num при возврате
                await station_obj.update_remain_num(self.db_pool, int(station_obj.remain_num) - 1)
            
            # Создаем запись о возврате в БД только если повербанк совместим
            await self._create_return_order(station_id, powerbank.powerbank_id)
            
            print(f"Повербанк {terminal_id} добавлен в слот {slot} станции {station_id} и данные обновлены в БД")
            
            # Автоматически запрашиваем инвентарь после успешного возврата
            await self._request_inventory_after_operation(station_id)
            
            # Отправляем успешный ответ
            return self._build_success_response(return_request)
            
        except Exception as e:
            print(f"Ошибка обработки запроса на возврат: {e}")
            return None
    
    async def _get_station_info(self, station_id: int) -> Optional[Dict[str, Any]]:
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
    
    async def _check_powerbank_station_compatibility(self, powerbank_org_unit_id: int, 
                                                   station_org_unit_id: int) -> bool:
        """
        Проверяет совместимость повербанка и станции с учетом иерархии групп/подгрупп
        
        Логика:
        - Если повербанк в группе → может перемещаться между станциями подгрупп этой группы
        - Если станция только в подгруппе → банки не могут перемещаться между станциями
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем информацию о группе повербанка
                    await cur.execute("""
                        SELECT unit_type, parent_org_unit_id 
                        FROM org_unit 
                        WHERE org_unit_id = %s
                    """, (powerbank_org_unit_id,))
                    powerbank_org = await cur.fetchone()
                    
                    # Получаем информацию о группе станции
                    await cur.execute("""
                        SELECT unit_type, parent_org_unit_id 
                        FROM org_unit 
                        WHERE org_unit_id = %s
                    """, (station_org_unit_id,))
                    station_org = await cur.fetchone()
                    
                    if not powerbank_org or not station_org:
                        return False
                    
                    powerbank_type, powerbank_parent = powerbank_org
                    station_type, station_parent = station_org
                    
                    # Если повербанк и станция в одной группе - совместимы
                    if powerbank_org_unit_id == station_org_unit_id:
                        return True
                    
                    # Если повербанк в группе, а станция в подгруппе этой группы
                    if (powerbank_type == 'group' and 
                        station_type == 'subgroup' and 
                        station_parent == powerbank_org_unit_id):
                        return True
                    
                    # Если повербанк в подгруппе, а станция в той же подгруппе
                    if (powerbank_type == 'subgroup' and 
                        station_type == 'subgroup' and 
                        powerbank_org_unit_id == station_org_unit_id):
                        return True
                    
                    # Если повербанк в подгруппе, а станция в родительской группе
                    if (powerbank_type == 'subgroup' and 
                        station_type == 'group' and 
                        powerbank_parent == station_org_unit_id):
                        return True
                    
                    # Повербанки подгрупп НЕ могут перемещаться между подгруппами
                    # (даже если они принадлежат одной родительской группе)
                    
                    return False
                    
        except Exception as e:
            print(f"Ошибка проверки совместимости: {e}")
            return False
    
    async def _send_force_eject_command(self, station_id: int, slot: int, connection) -> None:
        """Отправляет команду принудительной выдачи повербанка"""
        try:
            from utils.packet_utils import build_force_eject_request
            
            # Получаем секретный ключ станции
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для команды принудительной выдачи")
                return
            
            # Создаем команду на принудительное извлечение
            eject_command = build_force_eject_request(
                secret_key=secret_key,
                slot=slot,
                vsn=1
            )
            
            # Отправляем команду на станцию
            if hasattr(connection, 'writer') and connection.writer:
                connection.writer.write(eject_command)
                await connection.writer.drain()
                print(f"Отправлена команда принудительной выдачи для слота {slot} станции {station_id}")
            else:
                print(f"Нет соединения для отправки команды принудительной выдачи")
                
        except Exception as e:
            print(f"Ошибка отправки команды принудительной выдачи: {e}")
    
    def _build_success_response(self, return_request: Dict[str, Any]) -> bytes:
        """Создает успешный ответ на возврат"""
        slot = return_request.get("Slot")
        terminal_id = return_request.get("TerminalID")
        level = return_request.get("Level")
        voltage = return_request.get("Voltage")
        current = return_request.get("Current")
        temperature = return_request.get("Temperature")
        status = return_request.get("Status")
        soh = return_request.get("SOH")
        vsn = return_request.get("VSN")
        token = int(return_request.get("Token", "0x0"), 16)
        
        # Формируем статус байт
        status_byte = 0
        if status:
            status_byte = (status.get("LockStatus", 0) << 7 |
                          status.get("MicroUSBError", 0) << 2 |
                          status.get("TypeCError", 0) << 1 |
                          status.get("LightningError", 0))
        
        return build_return_power_bank_response(
            slot=slot,
            result=1,  # Success
            terminal_id=terminal_id.encode('ascii'),
            level=level,
            voltage=voltage,
            current=current,
            temperature=temperature,
            status=status_byte,
            soh=soh,
            vsn=vsn,
            token=token
        )
    
    def _build_error_response(self, return_request: Dict[str, Any], result: int = 0) -> bytes:
        """Создает ответ с ошибкой на возврат"""
        slot = return_request.get("Slot")
        terminal_id = return_request.get("TerminalID")
        level = return_request.get("Level")
        voltage = return_request.get("Voltage")
        current = return_request.get("Current")
        temperature = return_request.get("Temperature")
        status = return_request.get("Status")
        soh = return_request.get("SOH")
        vsn = return_request.get("VSN")
        token = int(return_request.get("Token", "0x0"), 16)
        
        # Формируем статус байт для ошибки
        status_byte = 1  # Error status
        
        return build_return_power_bank_response(
            slot=slot,
            result=result,  # Error code
            terminal_id=terminal_id.encode('ascii'),
            level=level,
            voltage=voltage,
            current=current,
            temperature=temperature,
            status=status_byte,
            soh=soh,
            vsn=vsn,
            token=token
        )
    
    async def _create_return_order(self, station_id: int, powerbank_id: int) -> None:
        """Создает запись о возврате повербанка в БД"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Сначала проверяем, есть ли пользователь с ID=1
                    await cur.execute("SELECT user_id FROM app_user WHERE user_id = 1 LIMIT 1")
                    user_exists = await cur.fetchone()
                    
                    if not user_exists:
                        # Если пользователя нет, создаем системного пользователя
                        await cur.execute("""
                            INSERT INTO app_user (user_id, username, email, password_hash, status, created_at)
                            VALUES (1, 'system', 'system@example.com', 'system', 'active', NOW())
                            ON DUPLICATE KEY UPDATE user_id = user_id
                        """)
                        await conn.commit()
                    
                    # Создаем запись о возврате
                    await cur.execute("""
                        INSERT INTO `orders` (station_id, user_id, powerbank_id, status, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (station_id, 1, powerbank_id, 'return'))
                    
                    print(f"Создана запись о возврате повербанка {powerbank_id} в станцию {station_id}")
                    
        except Exception as e:
            print(f"Ошибка создания записи о возврате: {e}")
    
    async def process_successful_return(self, station_id: int, powerbank_id: int, 
                                      slot_number: int, level: int, voltage: int, 
                                      temperature: int) -> None:
        """
        Обрабатывает успешный возврат повербанка
        Добавляет повербанк в station_powerbank
        """
        try:
            station_powerbank = await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank_id, slot_number,
                level, voltage, temperature
            )
            
            print(f"Повербанк {powerbank_id} успешно добавлен в слот {slot_number} станции {station_id}")
            
        except Exception as e:
            print(f"Ошибка при добавлении повербанка в станцию: {e}")
    
    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции с повербанком
        """
        try:
            from handlers.query_inventory import QueryInventoryHandler
            inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            result = await inventory_handler.send_inventory_request(station_id)
            if result["success"]:
                print(f"📦 Запрос инвентаря отправлен после операции возврата")
            else:
                print(f"❌ Ошибка отправки запроса инвентаря: {result['message']}")
        except Exception as e:
            print(f"❌ Ошибка запроса инвентаря после операции: {e}")
