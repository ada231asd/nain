"""
Обработчик для работы со станциями
"""
import asyncio
from typing import Optional, Tuple
from datetime import datetime

from models.station import Station
from models.powerbank import Powerbank
from models.station_powerbank import StationPowerbank
from models.connection import StationConnection
from utils.packet_utils import parse_login_packet, build_login_response, build_heartbeat_response, log_packet
from utils.powerbank_status_monitor import PowerbankStatusMonitor
from utils.centralized_logger import get_logger


class StationHandler:
    """Обработчик для работы со станциями"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.status_monitor = PowerbankStatusMonitor(db_pool)
        self.logger = get_logger('station_handler')
    
    async def handle_login(self, data: bytes, connection: StationConnection) -> Optional[bytes]:
        """
        Обрабатывает логин станции
        """
        try:
            # Логирование входящего пакета происходит в server.py
            
            # Парсим пакет логина
            packet = parse_login_packet(data)
            
            # Проверяем, есть ли ошибка парсинга
            if "Error" in packet:
                self.logger.error(f"Ошибка парсинга Login пакета: {packet['Error']}")
                return None
            
            logger = get_logger('station_handler'); logger.info(f"Обработан Login пакет: BoxID={packet['BoxID']}")
            
            # Получаем или создаем станцию
            station, secret_key = await Station.get_or_create(
                self.db_pool, 
                packet["BoxID"], 
                packet["SlotsNumDeclared"]
            )
            
            # Проверяем статус станции и наличие ключа
            if station.status == "pending" or secret_key is None:
                logger = get_logger('station_handler'); logger.warning(f"Станция {station.box_id} в статусе pending или нет ключа — соединение закрыто")
                return None
            
            # Создаем ответ на логин
            response, session_token = build_login_response(packet["VSN"], packet["Nonce"], secret_key)
            
            # Проверяем, не подключена ли уже эта станция
            existing_connection = self.connection_manager.get_connection_by_station_id(station.station_id)
            if existing_connection and existing_connection.fd != connection.fd:
                # Вычисляем время с последнего heartbeat
                from utils.time_utils import get_moscow_time
                current_time = get_moscow_time()
                time_since_heartbeat = (current_time - existing_connection.last_heartbeat).total_seconds()
                
                logger = get_logger('station_handler'); logger.warning(f"ПЕРЕПОДКЛЮЧЕНИЕ СТАНЦИИ: {station.box_id} - старое соединение fd={existing_connection.fd}, последний heartbeat {time_since_heartbeat:.1f} сек назад")
                
                # Безопасно закрываем старое соединение
                try:
                    if existing_connection.writer and not existing_connection.writer.is_closing():
                        existing_connection.writer.close()
                        print(f"ЗАКРЫТО СТАРОЕ СОЕДИНЕНИЕ: {station.box_id} (fd={existing_connection.fd}) - причина: переподключение")
                except Exception as close_error:
                    self.logger.error(f"Ошибка закрытия соединения: {close_error}")
                finally:
                    self.connection_manager.remove_connection(existing_connection.fd)
            
            # Обновляем данные соединения
            connection.update_login(
                box_id=packet["BoxID"],
                station_id=station.station_id,
                token=session_token,
                secret_key=secret_key
            )
            
            # Обновляем статус станции на active
            await station.update_status(self.db_pool, "active")
            
            # Обновляем last_seen при логине
            await station.update_last_seen(self.db_pool)
            
            # Синхронизируем данные повербанков с БД 
            await self._sync_powerbanks_to_db(station.station_id, packet["Slots"])
            
            # Синхронизируем station_powerbank с данными из пакета
            await StationPowerbank.sync_station_powerbanks(self.db_pool, station.station_id, packet["Slots"])
            
            # Обновляем remain_num в станции
            await station.update_remain_num(self.db_pool, packet["RemainNum"])
            
            # Инициализируем мониторинг статусов для станции
            await self.status_monitor.initialize_station(station.station_id)
            

            
            # Автоматически запрашиваем ICCID после успешного логина
            await self._request_iccid_after_login(connection)
            
            logger = get_logger('station_handler'); logger.info(f"Станция {station.box_id} успешно авторизована и обновлена в БД")
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
    
    async def handle_heartbeat(self, data: bytes, connection: StationConnection) -> Optional[bytes]:
        """Обрабатывает heartbeat пакет"""
        try:
            self.logger.info(f"Получен heartbeat от {connection.addr}, box_id: {connection.box_id}")
            
            # Проверяем, что соединение авторизовано
            if not connection.secret_key:
                self.logger.warning(f"Heartbeat от неавторизованного соединения {connection.addr}")
                return None
            
            # ВАЖНО: Валидируем токен в heartbeat пакете согласно протоколу
            if len(data) >= 9:  # Минимальная длина heartbeat пакета
                received_token = data[5:9]  # Токен находится в байтах 5-8
                payload = b''  # Для heartbeat payload пустой
                
                # Вычисляем ожидаемый токен
                import hashlib
                md5_hash = hashlib.md5(payload + connection.secret_key.encode()).digest()
                expected_token = bytes([
                    md5_hash[15],  # 16-я позиция
                    md5_hash[11],  # 12-я позиция  
                    md5_hash[7],   # 8-я позиция
                    md5_hash[3]    # 4-я позиция
                ])
                
                if received_token != expected_token:
                    self.logger.warning(f"Неверный токен в heartbeat от {connection.box_id}: получено {received_token.hex()}, ожидалось {expected_token.hex()}")
                    return None
                
                self.logger.info(f"Токен в heartbeat валиден для станции {connection.box_id}")
            else:
                self.logger.warning(f"Слишком короткий heartbeat пакет от {connection.box_id}: {len(data)} байт")
                return None
            
            # Получаем VSN из пакета
            vsn = data[3]
            self.logger.info(f"VSN из heartbeat: {vsn}")
            
            # Генерируем ответ с новым токеном
            response = build_heartbeat_response(connection.secret_key, vsn, connection.box_id or "unknown")
            self.logger.info(f"Сгенерирован heartbeat ответ: {response.hex() if response else 'None'}")
            
            if not response:
                self.logger.error("Heartbeat response не был создан!")
                return None
            
            # Обновляем время последнего heartbeat
            connection.update_heartbeat()
            
            self.logger.info(f"Heartbeat ответ готов к отправке: {len(response)} байт")
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки heartbeat: {e}")
            return None
    
    async def _update_heartbeat_db_async(self, connection: StationConnection):
        """
        Асинхронно обновляет БД для heartbeat (не блокирует ответ)
        """
        try:
            # Проверяем, нужно ли обновлять БД (не чаще чем раз в 30 секунд)
            from utils.time_utils import get_moscow_time
            current_time = get_moscow_time()
            if (not hasattr(connection, 'last_db_update') or 
                connection.last_db_update is None or
                (current_time - connection.last_db_update).total_seconds() > 30):
                
                station = await Station.get_by_id(self.db_pool, connection.station_id)
                if station:
                    # Обновляем время последнего контакта (last_seen)
                    await station.update_last_seen(self.db_pool)
                    
                    # Синхронизируем station_powerbank с текущим состоянием станции
                    from models.station_powerbank import StationPowerbank
                    current_powerbanks = await StationPowerbank.get_by_station(self.db_pool, connection.station_id)
                    
                    # Обновляем remain_num на основе реального количества повербанков
                    actual_remain_num = station.slots_declared - len(current_powerbanks)
                    if actual_remain_num != station.remain_num:
                        await station.update_remain_num(self.db_pool, actual_remain_num)
                        logger = get_logger('station_handler'); logger.info(f"Обновлен remain_num для станции {connection.box_id}: {station.remain_num} -> {actual_remain_num}")
                    
                    logger = get_logger('station_handler'); logger.info(f"Обновлен heartbeat для станции {connection.box_id} (ID: {connection.station_id})")
                    
                    # Запоминаем время последнего обновления БД
                    connection.last_db_update = current_time
        except Exception as db_error:
            self.logger.error(f"Ошибка обновления heartbeat в БД: {db_error}")
    
    async def _request_inventory_after_login(self, connection: StationConnection) -> None:
        """Запрашивает инвентарь после успешного логина"""
        try:
            if not connection.writer or connection.writer.is_closing():
                logger = get_logger('station_handler'); logger.warning("Соединение недоступно для запроса инвентаря")
                return
            
            from handlers.query_inventory import QueryInventoryHandler
            inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            await inventory_handler.send_inventory_request(connection.station_id)
            logger = get_logger('station_handler'); logger.info(f" Запрос инвентаря отправлен на станцию {connection.box_id}")
        except Exception as e:
            logger = get_logger('station_handler'); logger.error(f"Ошибка запроса инвентаря: {e}")
    
    async def _request_iccid_after_login(self, connection: StationConnection) -> None:
        """Автоматически запрашивает ICCID после успешного логина только если его нет в БД"""
        try:
            if not connection.writer or connection.writer.is_closing():
                logger = get_logger('station_handler'); logger.warning("Соединение недоступно для запроса ICCID")
                return
            
            # Проверяем, есть ли уже ICCID у станции
            station = await Station.get_by_id(self.db_pool, connection.station_id)
            if station and station.iccid:
                logger = get_logger('station_handler'); logger.info(f"ICCID уже есть у станции {connection.box_id}: {station.iccid}")
                return
            
            # Создаем запрос ICCID
            from utils.packet_utils import build_query_iccid_request
            iccid_request = build_query_iccid_request(connection.secret_key, vsn=1)
            
            # Отправляем запрос
            connection.writer.write(iccid_request)
            await connection.writer.drain()
            
            logger = get_logger('station_handler'); logger.info(f"Запрос ICCID отправлен станции {connection.box_id} (ICCID отсутствует в БД)")
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def _sync_powerbanks_to_db(self, station_id: int, slots_data: list) -> None:
        """Синхронизирует данные повербанков с БД (как в старом сервере)"""
        
        # Получаем org_unit_id станции
        station = await Station.get_by_id(self.db_pool, station_id)
        if not station:
            logger = get_logger('station_handler'); logger.info(f"Станция {station_id} не найдена")
            return
        
        for slot in slots_data:
            terminal_id = slot.get('TerminalID')
            if not terminal_id or terminal_id == '0000000000000000':
                continue  # Пропускаем пустые слоты
            
            # Проверяем, существует ли повербанк в БД
            existing_powerbank = await Powerbank.get_by_serial(self.db_pool, terminal_id)
            
            if existing_powerbank:
                # Проверяем совместимость групп - выплевываем повербанки других групп
                from utils.org_unit_utils import is_powerbank_compatible, get_compatibility_reason
                
                compatible = await is_powerbank_compatible(
                    self.db_pool, existing_powerbank.org_unit_id, station.org_unit_id
                )
                
                if not compatible:
                    reason = await get_compatibility_reason(
                        self.db_pool, existing_powerbank.org_unit_id, station.org_unit_id
                    )
                    logger = get_logger('station_handler')
                    logger.info(f"Повербанк {terminal_id} (org_unit {existing_powerbank.org_unit_id}) не совместим со станцией {station.org_unit_id} — выплёвываем. Причина: {reason}")
                    
                    # Логируем событие выплева
                    from utils.org_unit_utils import log_powerbank_ejection_event
                    await log_powerbank_ejection_event(
                        self.db_pool, station_id, slot['Slot'], terminal_id,
                        existing_powerbank.org_unit_id, station.org_unit_id, reason
                    )
                    
                    # Планируем извлечение несовместимого повербанка
                    await self._schedule_incompatible_powerbank_ejection(station_id, slot['Slot'], terminal_id)
                    continue
                
                # Обновляем SOH если есть данные
                if slot.get('SOH') is not None:
                    # Конвертируем SOH в int, чтобы избежать MySQL warnings
                    soh_int = int(slot['SOH']) if slot['SOH'] is not None else 0
                    await existing_powerbank.update_soh(self.db_pool, soh_int)
            else:
                # Создаем новый повербанк со статусом unknown в группе 1 
                new_powerbank = await Powerbank.create_unknown(
                    self.db_pool, 
                    terminal_id, 
                    1  # Группа 1 - глобальная сервисная группа
                )
                logger = get_logger('station_handler'); logger.info(f"Создан новый повербанк {terminal_id} со статусом unknown в группе 1 (ID: {new_powerbank.powerbank_id})")
                
                # Обновляем SOH если есть данные
                if slot.get('SOH') is not None:
                    # Конвертируем SOH в int, чтобы избежать MySQL warnings
                    soh_int = int(slot['SOH']) if slot['SOH'] is not None else 0
                    await new_powerbank.update_soh(self.db_pool, soh_int)
    
    async def _check_and_extract_incompatible_powerbanks(self, station_id: int) -> None:
        """Проверяет и извлекает несовместимые повербанки"""
        try:
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                logger = get_logger('station_handler'); logger.warning(f"Соединение для станции {station_id} не найдено")
                return
            
            # Используем обработчик извлечения для проверки совместимости
            from handlers.eject_powerbank import EjectPowerbankHandler
            eject_handler = EjectPowerbankHandler(self.db_pool, self.connection_manager)
            await eject_handler.check_and_extract_incompatible_powerbanks(station_id, connection)
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def _schedule_incompatible_powerbank_ejection(self, station_id: int, slot_number: int, terminal_id: str) -> None:
        """Планирует извлечение несовместимого повербанка"""
        try:
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                logger = get_logger('station_handler'); logger.info(f"Соединение для станции {station_id} не найдено для извлечения повербанка")
                return
            
            # Используем обработчик извлечения
            from handlers.eject_powerbank import EjectPowerbankHandler
            eject_handler = EjectPowerbankHandler(self.db_pool, self.connection_manager)
            await eject_handler.extract_incompatible_powerbank(station_id, slot_number, terminal_id, connection)
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
