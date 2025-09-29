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
    
    async def handle_login(self, data: bytes, connection: StationConnection) -> Optional[bytes]:
        """
        Обрабатывает логин станции
        Возвращает ответный пакет или None если соединение должно быть закрыто
        """
        try:
            # Логируем входящий пакет логина
            log_packet(data, "INCOMING", "unknown", "Login")
            
            # Парсим пакет логина
            packet = parse_login_packet(data)
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
                logger = get_logger('station_handler'); logger.warning(f"Станция {station.box_id} уже подключена через fd={existing_connection.fd}, закрываем старое соединение")
                # Безопасно закрываем старое соединение
                try:
                    if existing_connection.writer and not existing_connection.writer.is_closing():
                        existing_connection.writer.close()
                except Exception as close_error:
                    self.logger.error(f"Ошибка: {e}")
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
            
            # Синхронизируем данные повербанков с БД (создаем активные повербанки в группе станции)
            await self._sync_powerbanks_to_db(station.station_id, packet["Slots"])
            
            # Синхронизируем station_powerbank с данными из пакета
            await StationPowerbank.sync_station_powerbanks(self.db_pool, station.station_id, packet["Slots"])
            
            # Обновляем remain_num в станции
            await station.update_remain_num(self.db_pool, packet["RemainNum"])
            
            # Инициализируем мониторинг статусов для станции
            await self.status_monitor.initialize_station(station.station_id)
            
            # Автоматически запрашиваем инвентарь после успешного логина
            # (проверка совместимости повербанков выполнится автоматически после получения ответа)
            await self._request_inventory_after_login(connection)
            
            # Автоматически запрашиваем ICCID после успешного логина
            await self._request_iccid_after_login(connection)
            
            logger = get_logger('station_handler'); logger.info(f"Станция {station.box_id} успешно авторизована и обновлена в БД")
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
    
    async def handle_heartbeat(self, data: bytes, connection: StationConnection) -> Optional[bytes]:
        """
        Обрабатывает heartbeat от станции
        Возвращает ответный пакет
        """
        try:
            if not connection.secret_key:
                logger = get_logger('station_handler'); logger.warning("Нет секретного ключа для heartbeat")
                return None
            
            # Логируем входящий пакет с информацией о станции
            log_packet(data, "INCOMING", connection.box_id or "unknown", "Heartbeat")
            
            # Извлекаем VSN из пакета
            vsn = data[3]
            
            # Создаем ответ на heartbeat
            response = build_heartbeat_response(connection.secret_key, vsn)
            
            # Обновляем время последнего heartbeat
            connection.update_heartbeat()
            
            # Обновляем last_seen в базе данных
            if connection.station_id:
                try:
                    station = await Station.get_by_id(self.db_pool, connection.station_id)
                    if station:
                        # Обновляем время последнего контакта (last_seen)
                        await station.update_last_seen(self.db_pool)
                        
                        # Синхронизируем station_powerbank с текущим состоянием станции
                        # Получаем текущие данные о повербанках в станции
                        from models.station_powerbank import StationPowerbank
                        current_powerbanks = await StationPowerbank.get_by_station(self.db_pool, connection.station_id)
                        
                        # Обновляем remain_num на основе реального количества повербанков
                        actual_remain_num = station.slots_declared - len(current_powerbanks)
                        if actual_remain_num != station.remain_num:
                            await station.update_remain_num(self.db_pool, actual_remain_num)
                            logger = get_logger('station_handler'); logger.info(f"Обновлен remain_num для станции {connection.box_id}: {station.remain_num} -> {actual_remain_num}")
                        
                        logger = get_logger('station_handler'); logger.info(f"Обновлен heartbeat для станции {connection.box_id} (ID: {connection.station_id})")
                except Exception as db_error:
                    self.logger.error(f"Ошибка: {e}")
            
            logger = get_logger('station_handler'); logger.info(f"Heartbeat от станции {connection.box_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
    
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
                if existing_powerbank.org_unit_id != station.org_unit_id:
                    logger = get_logger('station_handler'); logger.info(f"Повербанк {terminal_id} из группы {existing_powerbank.org_unit_id} не принадлежит группе станции {station.org_unit_id} - выплевываем")
                    
                    # Планируем извлечение несовместимого повербанка
                    await self._schedule_incompatible_powerbank_ejection(station_id, slot['Slot'], terminal_id)
                    continue
                
                # Обновляем SOH если есть данные
                if slot.get('SOH') is not None:
                    # Конвертируем SOH в int, чтобы избежать MySQL warnings
                    soh_int = int(slot['SOH']) if slot['SOH'] is not None else 0
                    await existing_powerbank.update_soh(self.db_pool, soh_int)
            else:
                # Создаем новый повербанк со статусом unknown в группе 1 (глобальная сервисная группа)
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
