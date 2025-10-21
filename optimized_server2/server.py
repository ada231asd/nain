"""
Оптимизированный сервер с TCP и HTTP серверами
"""
import asyncio
import hashlib
import signal
import sys
import platform
from typing import Optional

import aiomysql
from aiohttp import web

from config.settings import SERVER_IP, TCP_PORTS, HTTP_PORT, DB_CONFIG, CONNECTION_TIMEOUT, MAX_PACKET_SIZE
from models.connection import ConnectionManager, StationConnection
from models.station import Station
from handlers.station_handler import StationHandler
from handlers.borrow_powerbank import BorrowPowerbankHandler
from handlers.return_powerbank import ReturnPowerbankHandler
from handlers.normal_return_powerbank import NormalReturnPowerbankHandler
from handlers.eject_powerbank import EjectPowerbankHandler
from handlers.query_iccid import QueryICCIDHandler
from handlers.slot_abnormal_report import SlotAbnormalReportHandler
from handlers.restart_cabinet import RestartCabinetHandler
from handlers.query_inventory import QueryInventoryHandler
from handlers.query_voice_volume import QueryVoiceVolumeHandler
from handlers.set_voice_volume import SetVoiceVolumeHandler
from handlers.set_server_address import SetServerAddressHandler
from handlers.query_server_address import QueryServerAddressHandler
from http_server import HTTPServer
from utils.packet_utils import parse_packet
from utils.station_resolver import StationResolver
from utils.centralized_logger import get_logger, close_logger, get_logger_stats
from utils.tcp_packet_logger import close_tcp_logger, get_tcp_logger_stats



class OptimizedServer:
   
    
    def __init__(self):
        self.db_pool: Optional[aiomysql.Pool] = None
        self.connection_manager = ConnectionManager()
        self.station_resolver = StationResolver(self.connection_manager)
        self.logger = get_logger('server')
        self.station_handler: Optional[StationHandler] = None
        self.borrow_handler: Optional[BorrowPowerbankHandler] = None
        self.return_handler: Optional[ReturnPowerbankHandler] = None
        self.normal_return_handler: Optional[NormalReturnPowerbankHandler] = None
        self.eject_handler: Optional[EjectPowerbankHandler] = None
        self.query_iccid_handler: Optional[QueryICCIDHandler] = None
        self.slot_abnormal_report_handler: Optional[SlotAbnormalReportHandler] = None
        self.restart_cabinet_handler: Optional[RestartCabinetHandler] = None
        self.query_inventory_handler: Optional[QueryInventoryHandler] = None
        self.query_voice_volume_handler: Optional[QueryVoiceVolumeHandler] = None
        self.set_voice_volume_handler: Optional[SetVoiceVolumeHandler] = None
        self.set_server_address_handler: Optional[SetServerAddressHandler] = None
        self.query_server_address_handler: Optional[QueryServerAddressHandler] = None
        self.tcp_servers: list[asyncio.Server] = []
        self.http_server: Optional[HTTPServer] = None
        self.running = False
        
    
    async def initialize_database(self):
        """Инициализирует подключение к базе данных"""
        try:
            self.db_pool = await aiomysql.create_pool(**DB_CONFIG)
            print("Подключение к базе данных установлено")
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            sys.exit(1)
    
    async def cleanup_database(self):
        """Закрывает подключение к базе данных"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            print("Подключение к базе данных закрыто")
    
    async def send_command_to_station(self, command_bytes: bytes, connection, station_info: dict) -> bool:
        """Отправляет команду на станцию через правильное соединение"""
        try:
            if connection.writer and not connection.writer.is_closing():
                # Логируем команду, отправляемую на станцию
                from utils.packet_utils import log_packet
                log_packet(command_bytes, "OUTGOING", connection.box_id or "unknown", "Command")
                connection.writer.write(command_bytes)
                await connection.writer.drain()
                return True
            else:
                self.logger.error(f"TCP соединение со станцией {connection.box_id} недоступно (writer закрыт)")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды станции {connection.box_id}: {e}")
            return False

    async def _validate_packet(self, data: bytes, connection: StationConnection) -> bool:
        """Валидация пакета согласно протоколу: checksum"""
        packet_data_len = int.from_bytes(data[0:2], byteorder='big')
        
        if len(data) < 2 + packet_data_len:
            return False

        command = data[2]
        vsn = data[3]
        checksum = data[4]
        token = data[5:9]
        
        # Извлекаем payload
        payload_start = 9
        payload_end = 2 + packet_data_len
        payload = data[payload_start:payload_end] if payload_end > payload_start else b''
        
        # Проверяем checksum для всех пакетов
        calculated_checksum = 0
        for byte in payload:
            calculated_checksum ^= byte
            
        if checksum != calculated_checksum:
            print(f"Неверная checksum: получено 0x{checksum:02X}, ожидалось 0x{calculated_checksum:02X}")
            return False
        
        return True

    async def _validate_token(self, connection: StationConnection, payload: bytes, received_token: bytes) -> bool:
        """Валидация токена по алгоритму MD5(payload + SecretKey)"""
        try:
            if not connection.box_id:
                return False
                
            # Получаем секретный ключ из базы данных
            secret_key = await self._get_secret_key_for_station(connection.box_id)
            if not secret_key:
                print(f"Секретный ключ не найден для станции {connection.box_id}")
                return False
            
          
            from utils.packet_utils import generate_session_token
            expected_token_int = generate_session_token(payload, secret_key)
            expected_token = expected_token_int.to_bytes(4, byteorder='big')
            
            return received_token == expected_token
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации токена: {e}")
            return False

    async def _get_secret_key_for_station(self, box_id: str) -> str:
        """Получает секретный ключ для станции из базы данных"""
        try:
            if not self.db_pool:
                return None
                
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    
                    await cur.execute("""
                        SELECT ssk.key_value 
                        FROM station_secret_key ssk
                        JOIN station s ON ssk.station_id = s.station_id
                        WHERE s.box_id = %s
                    """, (box_id,))
                    result = await cur.fetchone()
                    return result[0] if result else None
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения секретного ключа: {e}")
            return None

    async def _process_packet_data(self, data: bytes, connection: StationConnection, writer):
        """Обработка данных пакета (вынесена в отдельный метод)"""
        try:
            command = data[2]
            response = None
            
            # Определяем название команды
            command_names = {
                0x60: "Login", 0x61: "Heartbeat", 0x63: "SetServerAddress",
                0x64: "QueryInventory", 0x65: "BorrowPowerBank", 0x66: "ReturnPowerBank",
                0x67: "RestartCabinet", 0x69: "QueryICCID", 0x6A: "QueryServerAddress", 
                0x70: "SetVoiceVolume", 0x77: "QueryVoiceVolume", 0x80: "ForceEject",
                0x83: "SlotAbnormalReport"
            }
            command_name = command_names.get(command, f"Unknown(0x{command:02X})")
            
            
            # Логируем входящий пакет
            from utils.packet_utils import log_packet
            log_packet(data, "INCOMING", connection.box_id or "unknown", command_name)
            
            # Обработка команд
            if command == 0x60:  # Login
                if not self.station_handler:
                    self.logger.error("StationHandler не инициализирован!")
                    return False
                response = await self.station_handler.handle_login(data, connection)
                if response is None:
                    return True  # signal to close connection
                else:
                    try:
                        writer.write(response)
                        await writer.drain()
                        print(f" Ответ Login отправлен станции {connection.box_id}")
                        response = None  # Уже отправлен
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки Login ответа: {e}")
                        return True  # Закрываем соединение при ошибке отправки
            
            elif command == 0x61:  # Heartbeat
                response = await self.station_handler.handle_heartbeat(data, connection)
                if response:
                    try:
                        writer.write(response)
                        await writer.drain()
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки heartbeat ответа: {e}")
                    response = None
                else:
                    self.logger.warning(f"Heartbeat ответ не был создан для станции {connection.box_id}")
            
            elif command == 0x65:  # Borrow Power Bank
                # Проверяем, это запрос или ответ
                if len(data) >= 8:
                    if len(data) >= 12:
                        # Это ответ от станции на выдачу
                        await self.borrow_handler.handle_borrow_response(data, connection)
                    else:
                        # Это запрос на выдачу
                        response = await self.borrow_handler.handle_borrow_request(data, connection)
                        if response:
                            # Отправляем команду на станцию
                            writer.write(response)
                            await writer.drain()
                return False
            
            elif command == 0x66:  # Return Power Bank
                
                # Сначала проверяем, есть ли ожидающие возврат с ошибкой пользователи
                response = await self.return_handler.handle_tcp_error_return_request(data, connection)
                if response:
                    writer.write(response)
                    await writer.drain()
                return False
            
            elif command == 0x80:  # Force Eject Power Bank
                # Обрабатываем ответ на принудительное извлечение
                await self.eject_handler.handle_force_eject_response(data, connection)
                return False
            
            elif command == 0x69:  # Query ICCID
                # Обрабатываем ответ на запрос ICCID
                iccid_result = await self.query_iccid_handler.handle_query_iccid_response(data, connection)
                return False
            
            elif command == 0x83:  # Slot Status Abnormal Report
                # Обрабатываем отчет об аномалии слота
                abnormal_response = await self.slot_abnormal_report_handler.handle_slot_abnormal_report_request(data, connection)
                if abnormal_response:
                    writer.write(abnormal_response)
                    await writer.drain()
                return False
            
            elif command == 0x67:  # Restart Cabinet Response
                # Обрабатываем ответ на команду перезагрузки кабинета
                await self.restart_cabinet_handler.handle_restart_response(data, connection)
                return False
            
            elif command == 0x64:  # Query Inventory Response
                # Обрабатываем ответ на запрос инвентаря
                await self.query_inventory_handler.handle_inventory_response(data, connection)
                return False
            
            elif command == 0x77:  # Query Voice Volume Response
                # Обрабатываем ответ на запрос уровня громкости
                await self.query_voice_volume_handler.handle_voice_volume_response(data, connection)
                return False
            
            elif command == 0x70:  # Set Voice Volume Response
                # Обрабатываем ответ на установку уровня громкости
                await self.set_voice_volume_handler.handle_set_voice_volume_response(data, connection)
                return False
            
            elif command == 0x63:  # Set Server Address Response
                # Обрабатываем ответ на установку адреса сервера
                await self.set_server_address_handler.handle_set_server_address_response(data, connection)
                return False
            
            elif command == 0x6A:  # Query Server Address Response
                # Обрабатываем ответ на запрос адреса сервера
                await self.query_server_address_handler.handle_query_server_address_response(data, connection)
                return False
            
            else:
                self.logger.warning(f"Неизвестная команда 0x{command:02X} от станции {connection.box_id}")
                return False
            
            # Отправляем ответ
            if response and command != 0x61:
                # Проверяем соответствие writer и connection.fd
                writer_fd = writer.transport.get_extra_info('socket').fileno()
                if writer_fd != connection.fd:
                    self.logger.error(f"НЕСООТВЕТСТВИЕ: writer fd={writer_fd}, connection fd={connection.fd}")
                
                log_packet(response, "OUTGOING", connection.box_id or "unknown", f"{command_name}Response")
                writer.write(response)
                await writer.drain()
                print(f" Ответ {command_name} отправлен станции {connection.box_id}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки пакета: {e}")
            return False

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Обрабатывает подключение клиента"""
        fd = writer.transport.get_extra_info('socket').fileno()
        addr = writer.get_extra_info('peername')
        from utils.time_utils import get_moscow_time
        connection_time = get_moscow_time()
        
        self.logger.debug(f"Подключен: {addr} (fd={fd}) в {connection_time.strftime('%H:%M:%S')}")
        
        
        # Создаем соединение
        connection = StationConnection(fd, addr, writer=writer)
        self.connection_manager.add_connection(connection)
        connection_reset = False
        
        # Логируем информацию о подключении
        total_connections = len(self.connection_manager.get_all_connections())
        
        self.logger.debug(f"Подключен: {addr[0]}:{addr[1]} (fd={fd}) - Станция: {connection.box_id or 'Неизвестна'}")
        
        try:
            packet_count = 0
            while self.running:
                try:
                    packet_count += 1
                    
                    # Читаем заголовок пакета
                    try:
                        header = await reader.readexactly(2)
                        if not header:
                            break
                    except Exception as e:
                        break
                    
                    # Получаем длину данных из заголовка (big-endian)
                    packet_data_len = int.from_bytes(header, byteorder='big')
                    
                    # Читаем данные пакета
                    try:
                        packet_data = await reader.readexactly(packet_data_len)
                    except asyncio.IncompleteReadError as e:
                        break
                    except Exception as e:
                        break
                    
                    # Собираем полный пакет
                    data = header + packet_data
                    
                    if not await self._validate_packet(data, connection):
                        continue
                        
                except asyncio.IncompleteReadError as e:
                    break
                except Exception as e:
                    break
                
                # Обработка пакета
                should_close = await self._process_packet_data(data, connection, writer)
                if should_close:
                    break
        
        except asyncio.CancelledError:
            raise
        except ConnectionResetError as e:
            self.logger.warning(f"Соединение разорвано клиентом: {connection.box_id} ({addr}) - {e}")
            connection_reset = True
        except ConnectionAbortedError as e:
            self.logger.warning(f"Соединение прервано клиентом: {connection.box_id} ({addr}) - {e}")
            connection_reset = True
        except OSError as e:
            if e.errno == 104:  # Connection reset by peer
                self.logger.warning(f"Соединение сброшено станцией: {connection.box_id} ({addr}) - {e}")
                connection_reset = True
            else:
                self.logger.error(f"Сетевая ошибка: {connection.box_id} ({addr}) - {e}")
                connection_reset = True
        except Exception as e:
            self.logger.error(f"Ошибка обработки соединения {addr} (fd={fd}): {e}")
            connection_reset = False
        
        finally:
            # Закрываем соединение
            remaining_connections = len(self.connection_manager.get_all_connections())
            if connection_reset:
                self.logger.debug(f"Отключен: {addr} (fd={fd}) - сброс соединения клиентом, осталось соединений: {remaining_connections}")
            else:
                self.logger.debug(f"Отключен: {addr} (fd={fd}) - нормальное закрытие, осталось соединений: {remaining_connections}")
            self.connection_manager.remove_connection(fd)
            
            # Безопасное закрытие соединения
            try:
                if not writer.is_closing():
                    writer.close()
                    
                    if not connection_reset:
                        try:
                            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                        except asyncio.TimeoutError:
                            self.logger.debug(f"Таймаут при закрытии соединения {addr}")
                        except Exception as wait_error:
                            if not isinstance(wait_error, (ConnectionResetError, OSError)):
                                self.logger.error(f"Ошибка: {e}")
            except Exception as close_error:
            
                if not isinstance(close_error, (ConnectionResetError, OSError)):
                    self.logger.error(f"Ошибка: {e}")
    
    async def start_servers(self):
        """Запускает TCP и HTTP серверы"""
        try:
            # Инициализируем базу данных
            await self.initialize_database()
            
            # Создаем обработчики
            self.station_handler = StationHandler(self.db_pool, self.connection_manager)
            self.borrow_handler = BorrowPowerbankHandler(self.db_pool, self.connection_manager)
            self.return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            self.normal_return_handler = NormalReturnPowerbankHandler(self.db_pool, self.connection_manager)
            self.eject_handler = EjectPowerbankHandler(self.db_pool, self.connection_manager)
            self.query_iccid_handler = QueryICCIDHandler(self.db_pool, self.connection_manager)
            self.slot_abnormal_report_handler = SlotAbnormalReportHandler(self.db_pool, self.connection_manager)
            self.restart_cabinet_handler = RestartCabinetHandler(self.db_pool, self.connection_manager)
            self.query_inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            self.query_voice_volume_handler = QueryVoiceVolumeHandler(self.db_pool, self.connection_manager)
            self.set_voice_volume_handler = SetVoiceVolumeHandler(self.db_pool, self.connection_manager)
            self.set_server_address_handler = SetServerAddressHandler(self.db_pool, self.connection_manager)
            self.query_server_address_handler = QueryServerAddressHandler(self.db_pool, self.connection_manager)
            
            
            self.http_server = HTTPServer()
            self.http_server.db_pool = self.db_pool
            # Инъекция общего обработчика для последующего использования
            setattr(self.http_server, 'shared_borrow_handler', self.borrow_handler)
            # Инъекция обработчика возврата для использования
            setattr(self.http_server, 'shared_return_handler', self.return_handler)
            
            self.running = True
            
            # Запускаем TCP серверы на всех указанных портах
            print("TCP сервер запущен и слушает порты")
            for port in TCP_PORTS:
        
                server_kwargs = {
                    'reuse_address': True
                }
                if platform.system() == 'Linux':
                    server_kwargs['reuse_port'] = True
                
                server = await asyncio.start_server(
                    self.handle_client,
                    SERVER_IP,
                    port,
                    **server_kwargs
                )
                self.tcp_servers.append(server)
            
            # Запускаем HTTP сервер с connection_manager
            http_app = self.http_server.create_app(self.connection_manager)
            http_runner = web.AppRunner(http_app)
            await http_runner.setup()
            http_site = web.TCPSite(http_runner, '0.0.0.0', HTTP_PORT)
            await http_site.start()
            
            # Запускаем WebSocket сервер
            from websocket_server import WebSocketServer
            websocket_server = WebSocketServer(self.db_pool, self.connection_manager)
            ws_app = websocket_server.create_app()
            ws_runner = web.AppRunner(ws_app)
            await ws_runner.setup()
            ws_site = web.TCPSite(ws_runner, '0.0.0.0', 8001)
            await ws_site.start()
            print(f"HTTP сервер запущен на 0.0.0.0:{HTTP_PORT}")
            print(f"WebSocket сервер запущен на 0.0.0.0:8001")
            
            
            # Запускаем мониторинг соединений
            asyncio.create_task(self._connection_monitor())
            
            # Ждем завершения серверов
            try:
             
                await asyncio.gather(*(srv.serve_forever() for srv in self.tcp_servers))
                        
            except asyncio.CancelledError:
                print("TCP серверы остановлены")
            except Exception as e:
                self.logger.error(f"Ошибка: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
        finally:
 
            pass
    
    async def _connection_monitor(self):
        """Мониторинг соединений"""
        while self.running:
            try:
                # Очищаем неактивные соединения
                cleaned = self.connection_manager.cleanup_inactive_connections(120)
                if cleaned > 0:
                    self.logger.info(f"Очищено {cleaned} неактивных соединений")
                
                # Проверяем соединения только на дублирование
                connections = self.connection_manager.get_all_connections()
                if connections:
                    # Группируем по станциям для выявления дублирования
                    stations = {}
                    for fd, conn in connections.items():
                        if conn.station_id:
                            if conn.station_id not in stations:
                                stations[conn.station_id] = []
                            stations[conn.station_id].append((fd, conn))
                    
                    # Выводим информацию только о дублирующихся соединениях
                    for station_id, station_connections in stations.items():
                        if len(station_connections) > 1:
                            print(f"  Станция {station_id}: {len(station_connections)} соединений (дублирование!)")
                            for fd, conn in station_connections:
                                from utils.time_utils import get_moscow_time
                                current_time = get_moscow_time()
                                time_since_heartbeat = (current_time - conn.last_heartbeat).total_seconds()
                                print(f"  - fd={fd}, box_id={conn.box_id}, heartbeat={time_since_heartbeat:.1f} сек назад")
                    
                    # Очищаем дублирующиеся соединения - должно быть только 1 соединение на станцию
                    for station_id, station_connections in stations.items():
                        if len(station_connections) > 1:
                            print(f"Очищаем дублирующиеся соединения для станции {station_id}: {len(station_connections)} соединений")
                            # Оставляем только самое новое соединение
                            station_connections.sort(key=lambda x: x[1].last_heartbeat, reverse=True)
                            for fd, conn in station_connections[1:]:  # Удаляем все кроме первого
                                print(f"Закрываем дублирующееся соединение fd={fd}")
                                self.connection_manager.close_connection(fd)
                
                
                await asyncio.sleep(60)             
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге соединений: {e}")
                await asyncio.sleep(60)
    
    async def stop_servers(self):
        """Останавливает серверы"""
        print("Остановка серверов...")
        self.logger.info("Остановка серверов...")
        self.running = False
        
        # Деактивируем все станции перед закрытием
        await self._deactivate_all_stations()
        
        # Принудительно закрываем все TCP соединения
        await self._close_all_connections()
        
        # Закрываем все TCP серверы
        for server in self.tcp_servers:
            if server:
                server.close()
        
        if self.http_server:
            self.http_server.stop_server()
        
        # Закрываем базу данных после деактивации станций
        await self.cleanup_database()
        
        # Закрываем логгеры
        close_logger()
        close_tcp_logger()
        self.logger.info("Логгеры закрыты")
    
    async def _deactivate_all_stations(self):
        """Деактивирует все станции при закрытии сервера"""
        try:
            self.logger.info("Деактивация всех станций...")
            
            # Сначала деактивируем станции с активными соединениями
            connections = self.connection_manager.get_all_connections()
            active_stations = []
            
            for fd, conn in connections.items():
                if conn.station_id and conn.box_id:
                    active_stations.append((conn.station_id, conn.box_id))
            
            if active_stations:
                self.logger.info(f"Найдено {len(active_stations)} активных станций для деактивации")
                
                # Деактивируем каждую станцию
                for station_id, box_id in active_stations:
                    try:
                        # Проверяем, что пул соединений еще доступен
                        if not self.db_pool or self.db_pool._closed:
                            self.logger.warning("Пул соединений с БД уже закрыт")
                            continue
                            
                        station = await Station.get_by_id(self.db_pool, station_id)
                        if station:
                            await station.update_status(self.db_pool, "inactive")
                            self.logger.info(f"Станция {box_id} (ID: {station_id}) деактивирована")
                    except Exception as e:
                        # Игнорируем ошибки с закрытым пулом соединений
                        if "Cannot acquire connection after closing pool" in str(e):
                            self.logger.warning(f"Пул соединений закрыт, пропускаем деактивацию станции {box_id}")
                        else:
                            self.logger.error(f"Ошибка деактивации станции {box_id}: {e}")
            else:
                self.logger.info("Активных станций не найдено")
            
            await self._deactivate_all_active_stations_in_db()
                
        except Exception as e:
            self.logger.error(f"Ошибка при деактивации станций: {e}")
    
    async def _close_all_connections(self):
        """Принудительно закрывает все TCP соединения"""
        try:
            self.logger.info("Принудительное закрытие всех TCP соединений...")
            
            connections = self.connection_manager.get_all_connections()
            if not connections:
                return
            
            self.logger.info(f"Найдено {len(connections)} соединений для закрытия")
            
            closed_count = 0
            for fd, conn in connections.items():
                try:
                    if conn.writer and not conn.writer.is_closing():
                        self.logger.debug(f"Закрываем соединение {conn.addr} (станция: {conn.box_id})")
                        conn.writer.close()
                        await conn.writer.wait_closed()
                        closed_count += 1
                    else:
                        self.logger.debug(f"Соединение {conn.addr} уже закрыто")
                except Exception as e:
                    self.logger.error(f"Ошибка закрытия соединения {conn.addr}: {e}")
            
            self.logger.info(f"Закрыто {closed_count} соединений")
            
            # Очищаем менеджер соединений
            self.connection_manager.clear_all_connections()
            self.logger.info("Менеджер соединений очищен")
            
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии соединений: {e}")
    
    async def _deactivate_all_active_stations_in_db(self):
        """Деактивирует все станции со статусом 'active' в базе данных"""
        try:
            self.logger.info("Деактивация всех активных станций в БД...")
            
            # Проверяем, что пул соединений еще доступен
            if not self.db_pool or self.db_pool._closed:
                self.logger.warning("Пул соединений с БД уже закрыт")
                return
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем все активные станции
                    await cur.execute("SELECT station_id, box_id FROM station WHERE status = 'active'")
                    active_stations = await cur.fetchall()
                    
                    if active_stations:
                        self.logger.info(f"Найдено {len(active_stations)} активных станций в БД")
                        
                        # Деактивируем все активные станции
                        await cur.execute("UPDATE station SET status = 'inactive' WHERE status = 'active'")
                        affected_rows = cur.rowcount
                        
                        self.logger.info(f"Деактивировано {affected_rows} станций в БД")
                        
                        # Выводим информацию о деактивированных станциях
                        for station_id, box_id in active_stations:
                            self.logger.info(f"Станция {box_id} (ID: {station_id}) деактивирована")
                    else:
                        self.logger.info("Активных станций в БД не найдено")
                        
        except Exception as e:
            if "Cannot acquire connection after closing pool" in str(e):
                self.logger.warning("Пул соединений закрыт, пропускаем деактивацию станций в БД")
            else:
                self.logger.error(f"Ошибка при деактивации станций в БД: {e}")


async def main():
    """Основная функция"""
    server = OptimizedServer()
    
    # Обработчик сигналов для корректного завершения
    def signal_handler():
        print("Получен сигнал завершения")
        # Создаем задачу для асинхронного завершения
        asyncio.create_task(server.stop_servers())
    
    # Устанавливаем обработчики сигналов
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    else:
        def windows_signal_handler(signum, frame):
            signal_handler()
        
        signal.signal(signal.SIGINT, windows_signal_handler)
        signal.signal(signal.SIGTERM, windows_signal_handler)
    
    try:
        await server.start_servers()
    except KeyboardInterrupt:
        print("Получен сигнал прерывания")
    except asyncio.CancelledError:
        print("Сервер остановлен")
    except Exception as e:
        print(f"Ошибка сервера: {e}")
    finally:
        try:
            await server.stop_servers()
        except Exception as e:
            print(f"Ошибка при остановке сервера: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Серверы остановлены")
    except asyncio.CancelledError:
        print("Серверы остановлены")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)