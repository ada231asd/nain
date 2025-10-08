"""
Оптимизированный сервер с TCP и HTTP серверами
"""
import asyncio
import hashlib
import signal
import sys
from typing import Optional

import aiomysql
from aiohttp import web

from config.settings import SERVER_IP, TCP_PORTS, HTTP_PORT, DB_CONFIG, CONNECTION_TIMEOUT, MAX_PACKET_SIZE
from models.connection import ConnectionManager, StationConnection
from models.station import Station
from handlers.station_handler import StationHandler
from handlers.borrow_powerbank import BorrowPowerbankHandler
from handlers.return_powerbank import ReturnPowerbankHandler
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
        
        # Статистика для мониторинга производительности heartbeat'ов
        self.heartbeat_stats = {
            'total_processed': 0,
            'last_minute': 0,
            'last_reset': None,
            'max_per_second': 0,
            'current_per_second': 0
        }
    
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
      
        try:
            if connection.writer and not connection.writer.is_closing():
                # Логируем команду, отправляемую на станцию
                from utils.packet_utils import log_packet
                log_packet(command_bytes, "OUTGOING", connection.box_id or "unknown", "Command")
                connection.writer.write(command_bytes)
                await connection.writer.drain()
                return True
            else:
                print("TCP соединение со станцией недоступно")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return False

    async def _validate_packet(self, data: bytes, connection: StationConnection) -> bool:
        """Валидация пакета согласно протоколу: checksum и token"""
        try:
            packet_data_len = int.from_bytes(data[0:2], byteorder='big')
            
            # Проверяем базовую структуру пакета
            if len(data) < 2 + packet_data_len:
                print(f"Неполный пакет: ожидалось {2 + packet_data_len}, получено {len(data)}")
                return False
                
            # Структура пакета: [2 байта длина][1 байт команда][1 байт VSN][1 байт CheckSum][4 байта Token][Payload...]
            command = data[2]
            vsn = data[3]
            checksum = data[4]
            token = data[5:9]
            
            # Извлекаем payload (данные после токена)
            payload_start = 9
            payload_end = 2 + packet_data_len
            payload = data[payload_start:payload_end] if payload_end > payload_start else b''
            
            print(f"Парсинг пакета: команда=0x{command:02X}, VSN={vsn}, checksum=0x{checksum:02X}, payload_len={len(payload)}")
            
            # 1. Проверяем checksum (XOR payload)
            calculated_checksum = 0
            for byte in payload:
                calculated_checksum ^= byte
                
            if checksum != calculated_checksum:
                print(f"Неверная checksum: получено 0x{checksum:02X}, ожидалось 0x{calculated_checksum:02X}")
                return False
            
            # 2. Проверяем token (кроме команды Login)
            if command != 0x60:  # Login не требует проверки токена
                if not await self._validate_token(connection, payload, token):
                    print(f"Неверный токен для команды 0x{command:02X}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации пакета: {e}")
            return False

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
            
            # Вычисляем MD5 хеш
            md5_hash = hashlib.md5(payload + secret_key.encode()).digest()
            
            # Формируем ожидаемый токен по правилам
            expected_token = bytes([
                md5_hash[15],  # 16-я позиция
                md5_hash[11],  # 12-я позиция  
                md5_hash[7],   # 8-я позиция
                md5_hash[3]    # 4-я позиция
            ])
            
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
                    # Получаем secret_key из таблицы station_secret_key через JOIN с station
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
            
            print(f"Обрабатываем команду: 0x{command:02X}")
            
            # Логируем входящий пакет
            from utils.packet_utils import log_packet
            command_names = {
                0x60: "Login", 0x61: "Heartbeat", 0x63: "SetServerAddress",
                0x64: "QueryInventory", 0x65: "BorrowPowerBank", 0x66: "ReturnPowerBank",
                0x67: "RestartCabinet", 0x69: "QueryICCID", 0x6A: "QueryServerAddress", 
                0x70: "SetVoiceVolume", 0x77: "QueryVoiceVolume", 0x80: "ForceEject",
                0x83: "SlotAbnormalReport"
            }
            command_name = command_names.get(command, f"Unknown(0x{command:02X})")
            print(f"Название команды: {command_name}")
            log_packet(data, "INCOMING", connection.box_id or "unknown", command_name)
            
            # Обработка команд
            if command == 0x60:  # Login
                print("Обрабатываем команду Login")
                if not self.station_handler:
                    print("ОШИБКА: station_handler не инициализирован!")
                    return False
                response = await self.station_handler.handle_login(data, connection)
                print(f"Login response: {response}")
                if response is None:
                    print("Login failed, закрываем соединение")
                    return True  # signal to close connection
            
            elif command == 0x61:  # Heartbeat
                print(f"Обрабатываем Heartbeat от станции {connection.box_id}")
                response = await self.station_handler.handle_heartbeat(data, connection)
                if response:
                    try:
                        print(f"Отправляем heartbeat ответ станции {connection.box_id}: {response.hex()}")
                        writer.write(response)
                        await writer.drain()
                        print(f"Heartbeat ответ успешно отправлен станции {connection.box_id}")
                    except Exception as e:
                        print(f"Ошибка отправки heartbeat ответа: {e}")
                        self.logger.error(f"Ошибка отправки heartbeat ответа: {e}")
                    response = None
                else:
                    print(f"Heartbeat ответ не был создан для станции {connection.box_id}")
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
                if len(data) >= 21:  # Ответ на возврат
                    await self.return_handler.handle_return_response(data, connection)
                else:  # Запрос на возврат
                    response = await self.return_handler.handle_return_request(data, connection)
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
                print(f"Результат запроса ICCID: {iccid_result}")
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
                print(f"Неизвестная команда: {hex(command)}")
                return False
            
            # Отправляем ответ (heartbeat уже обработан выше)
            if response and command != 0x61:
                log_packet(response, "OUTGOING", connection.box_id or "unknown", f"{command_name}Response")
                writer.write(response)
                await writer.drain()
            
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
        print(f"Подключен: {addr} (fd={fd}) в {connection_time.strftime('%H:%M:%S')}")
        print(f"DEBUG: self.running = {self.running}")
        
        # Логируем статистику подключений
        if hasattr(self, 'connection_stats'):
            self.connection_stats['total_connections'] = getattr(self.connection_stats, 'total_connections', 0) + 1
        else:
            self.connection_stats = {'total_connections': 1}
        
        # Создаем соединение
        connection = StationConnection(fd, addr, writer=writer)
        self.connection_manager.add_connection(connection)
        connection_reset = False
        
        try:
            print(f"DEBUG: Начинаем цикл чтения, self.running = {self.running}")
            while self.running:
                try:
                    print(f"Ожидаем данные от {addr}...")
                    
                    # Читаем заголовок пакета (первые 2 байта - длина данных БЕЗ заголовка)
                    header = await reader.readexactly(2)
                    if not header:
                        print(f"Соединение закрыто клиентом {addr}")
                        break
                    
                    print(f"Получен заголовок от {addr}: {header.hex()}")
                    
                    # Получаем длину данных из заголовка (big-endian)
                    packet_data_len = int.from_bytes(header, byteorder='big')
                    print(f"Длина данных пакета: {packet_data_len} байт")
                    
                    # Валидация длины данных пакета
                    if packet_data_len < 5:  # Минимальная длина данных (Command + VSN + CheckSum + Token = 5 байт)
                        print(f"Некорректная длина данных пакета {packet_data_len} от {addr}")
                        continue
                    if packet_data_len > 1022:  # Максимальная разумная длина данных (1024 - 2 байта заголовка)
                        print(f"Слишком большая длина данных пакета {packet_data_len} от {addr}")
                        continue
                    
                    # Читаем данные пакета (БЕЗ заголовка) с таймаутом
                    print(f"Читаем {packet_data_len} байт данных...")
                    try:
                        packet_data = await asyncio.wait_for(
                            reader.readexactly(packet_data_len), 
                            timeout=5.0
                        )
                        print(f"Прочитано {len(packet_data)} байт данных")
                    except asyncio.TimeoutError:
                        print(f"ТАЙМАУТ: Не удалось прочитать {packet_data_len} байт за 5 секунд")
                        break
                    except asyncio.IncompleteReadError as e:
                        print(f"НЕПОЛНОЕ ЧТЕНИЕ: Ожидалось {packet_data_len}, прочитано {len(e.partial)}")
                        print(f"Частичные данные: {e.partial.hex()}")
                        break
                    
                    # Собираем полный пакет (заголовок + данные)
                    data = header + packet_data
                    
                    print(f"Получен пакет от {addr}: общая длина={len(data)}, данные={packet_data_len}")
                    print(f"Полный hex пакета: {data.hex()}")
                    
                    # ВАЖНО: Валидируем пакет перед обработкой
                    print(f"Начинаем валидацию пакета...")
                    if not await self._validate_packet(data, connection):
                        print(f"Невалидный пакет от {addr}, пропускаем")
                        continue
                    print(f"Пакет прошел валидацию, начинаем обработку...")
                        
                except asyncio.IncompleteReadError as e:
                    print(f"Неполное чтение данных от {addr}: {e}")
                    break
                except Exception as e:
                    print(f"Ошибка чтения данных от {addr}: {e}")
                    break
                
                # Обработка пакета
                print(f"Начинаем обработку пакета от {addr}")
                should_close = await self._process_packet_data(data, connection, writer)
                print(f"Обработка пакета завершена, should_close={should_close}")
                if should_close:
                    break
        
        except asyncio.CancelledError:
            print(f"Соединение {addr} отменено")
            raise
        except ConnectionResetError as e:
            print(f"СОЕДИНЕНИЕ РАЗОРВАНО КЛИЕНТОМ: {connection.box_id} ({addr}) - {e}")
            connection_reset = True
        except ConnectionAbortedError as e:
            print(f"СОЕДИНЕНИЕ ПРЕРВАНО КЛИЕНТОМ: {connection.box_id} ({addr}) - {e}")
            connection_reset = True
        except OSError as e:
            if e.errno == 104:  # Connection reset by peer
                print(f"СОЕДИНЕНИЕ СБРОШЕНО СТАНЦИЕЙ: {connection.box_id} ({addr}) - {e}")
                connection_reset = True
            else:
                print(f"СЕТЕВАЯ ОШИБКА: {connection.box_id} ({addr}) - {e}")
                connection_reset = True
        except Exception as e:
            print(f"ОШИБКА ОБРАБОТКИ: {connection.box_id} ({addr}) - {e}")
            self.logger.error(f"Ошибка обработки соединения {addr} (fd={fd}): {e}")
            connection_reset = False
        
        finally:
            # Закрываем соединение
            if connection_reset:
                print(f"Отключен: {addr} (fd={fd}) - сброс соединения клиентом")
            else:
                print(f"Отключен: {addr} (fd={fd}) - нормальное закрытие")
            self.connection_manager.remove_connection(fd)
            
            # Выводим статистику каждые 10 подключений
            if hasattr(self, 'connection_stats') and self.connection_stats['total_connections'] % 10 == 0:
                active_connections = len(self.connection_manager.get_all_connections())
                print(f"Статистика: всего подключений {self.connection_stats['total_connections']}, активных {active_connections}")
            
            # Безопасное закрытие соединения
            try:
                if not writer.is_closing():
                    writer.close()
                    
                    if not connection_reset:
                        try:
                            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                        except asyncio.TimeoutError:
                            print(f"Таймаут при закрытии соединения {addr}")
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
            self.eject_handler = EjectPowerbankHandler(self.db_pool, self.connection_manager)
            self.query_iccid_handler = QueryICCIDHandler(self.db_pool, self.connection_manager)
            self.slot_abnormal_report_handler = SlotAbnormalReportHandler(self.db_pool, self.connection_manager)
            self.restart_cabinet_handler = RestartCabinetHandler(self.db_pool, self.connection_manager)
            self.query_inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            self.query_voice_volume_handler = QueryVoiceVolumeHandler(self.db_pool, self.connection_manager)
            self.set_voice_volume_handler = SetVoiceVolumeHandler(self.db_pool, self.connection_manager)
            self.set_server_address_handler = SetServerAddressHandler(self.db_pool, self.connection_manager)
            self.query_server_address_handler = QueryServerAddressHandler(self.db_pool, self.connection_manager)
            
            # Создаем HTTP сервер
            self.http_server = HTTPServer()
            self.http_server.db_pool = self.db_pool
            
    
            # Устанавливаем running = True ПЕРЕД запуском серверов
            self.running = True
            
            # Запускаем TCP серверы на всех указанных портах
            print(f"Запуск TCP серверов на портах: {TCP_PORTS}")
            for port in TCP_PORTS:
                server = await asyncio.start_server(
                    self.handle_client,
                    SERVER_IP,
                    port,
                    reuse_address=True,
                    reuse_port=True
                )
                self.tcp_servers.append(server)
                print(f"TCP сервер запущен на {SERVER_IP}:{port}")
            
            print(f"Всего запущено {len(self.tcp_servers)} TCP серверов")
            
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
            print(f"Сервер мониторинга запущен на 0.0.0.0:8002")
            
            
            # Запускаем мониторинг соединений
            asyncio.create_task(self._connection_monitor())
            
           
            
            # Ждем завершения серверов
            try:
                # Запускаем все TCP серверы параллельно
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
                # Очищаем неактивные соединения (таймаут 2 минуты для стабильности)
                cleaned = self.connection_manager.cleanup_inactive_connections(120)
                if cleaned > 0:
                    print(f"Очищено {cleaned} неактивных соединений")
                
                # Выводим статистику соединений
                connections = self.connection_manager.get_all_connections()
                if connections:
                    # Группируем по станциям для выявления дублирования
                    stations = {}
                    for fd, conn in connections.items():
                        if conn.station_id:
                            if conn.station_id not in stations:
                                stations[conn.station_id] = []
                            stations[conn.station_id].append((fd, conn))
                    
                    # Очищаем дублирующиеся соединения
                    for station_id, station_connections in stations.items():
                        if len(station_connections) > 1:
                            print(f"Очищаем дублирующиеся соединения для станции {station_id}")
                            # Оставляем только самое новое соединение
                            station_connections.sort(key=lambda x: x[1].last_heartbeat, reverse=True)
                            for fd, conn in station_connections[1:]:  # Удаляем все кроме первого
                                print(f"Закрываем дублирующееся соединение fd={fd}")
                                self.connection_manager.close_connection(fd)
                
                # Выводим статистику heartbeat'ов
                if self.heartbeat_stats['total_processed'] > 0:
                    if self.heartbeat_stats['current_per_second'] > self.heartbeat_stats['max_per_second']:
                        self.heartbeat_stats['max_per_second'] = self.heartbeat_stats['current_per_second']
                    self.heartbeat_stats['current_per_second'] = 0
                
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
            except Exception as e:
                self.logger.error(f"Ошибка: {e}")
                await asyncio.sleep(30)
    
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
        print("Логгеры закрыты")
    
    async def _deactivate_all_stations(self):
        """Деактивирует все станции при закрытии сервера"""
        try:
            print(" Деактивация всех станций...")
            
            # Сначала деактивируем станции с активными соединениями
            connections = self.connection_manager.get_all_connections()
            active_stations = []
            
            for fd, conn in connections.items():
                if conn.station_id and conn.box_id:
                    active_stations.append((conn.station_id, conn.box_id))
            
            if active_stations:
                print(f" Найдено {len(active_stations)} активных станций для деактивации")
                
                # Деактивируем каждую станцию
                for station_id, box_id in active_stations:
                    try:
                        # Проверяем, что пул соединений еще доступен
                        if not self.db_pool or self.db_pool._closed:
                            print(f" Пул соединений с БД уже закрыт")
                            continue
                            
                        station = await Station.get_by_id(self.db_pool, station_id)
                        if station:
                            await station.update_status(self.db_pool, "inactive")
                            print(f" Станция {box_id} (ID: {station_id}) деактивирована")
                    except Exception as e:
                        # Игнорируем ошибки с закрытым пулом соединений
                        if "Cannot acquire connection after closing pool" in str(e):
                            print(f" Пул соединений закрыт, пропускаем деактивацию станции {box_id}")
                        else:
                            print(f" Ошибка деактивации станции {box_id}: {e}")
            else:
                print(" Активных станций не найдено")
            
            await self._deactivate_all_active_stations_in_db()
                
        except Exception as e:
            print(f" Ошибка при деактивации станций: {e}")
    
    async def _close_all_connections(self):
        """Принудительно закрывает все TCP соединения"""
        try:
            print(" Принудительное закрытие всех TCP соединений...")
            
            connections = self.connection_manager.get_all_connections()
            if not connections:
                return
            
            print(f" Найдено {len(connections)} соединений для закрытия")
            
            closed_count = 0
            for fd, conn in connections.items():
                try:
                    if conn.writer and not conn.writer.is_closing():
                        print(f" Закрываем соединение {conn.addr} (станция: {conn.box_id})")
                        conn.writer.close()
                        await conn.writer.wait_closed()
                        closed_count += 1
                    else:
                        print(f" Соединение {conn.addr} уже закрыто")
                except Exception as e:
                    print(f" Ошибка закрытия соединения {conn.addr}: {e}")
            
            print(f" Закрыто {closed_count} соединений")
            
            # Очищаем менеджер соединений
            self.connection_manager.clear_all_connections()
            print(" Менеджер соединений очищен")
            
        except Exception as e:
            print(f" Ошибка при закрытии соединений: {e}")
    
    async def _deactivate_all_active_stations_in_db(self):
        """Деактивирует все станции со статусом 'active' в базе данных"""
        try:
            print(" Деактивация всех активных станций в БД...")
            
            # Проверяем, что пул соединений еще доступен
            if not self.db_pool or self.db_pool._closed:
                print(" Пул соединений с БД уже закрыт")
                return
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем все активные станции
                    await cur.execute("SELECT station_id, box_id FROM station WHERE status = 'active'")
                    active_stations = await cur.fetchall()
                    
                    if active_stations:
                        print(f" Найдено {len(active_stations)} активных станций в БД")
                        
                        # Деактивируем все активные станции
                        await cur.execute("UPDATE station SET status = 'inactive' WHERE status = 'active'")
                        affected_rows = cur.rowcount
                        
                        print(f" Деактивировано {affected_rows} станций в БД")
                        
                        # Выводим информацию о деактивированных станциях
                        for station_id, box_id in active_stations:
                            print(f"  - Станция {box_id} (ID: {station_id})")
                    else:
                        print(" Активных станций в БД не найдено")
                        
        except Exception as e:
            if "Cannot acquire connection after closing pool" in str(e):
                print(" Пул соединений закрыт, пропускаем деактивацию станций в БД")
            else:
                print(f" Ошибка при деактивации станций в БД: {e}")


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

    

    async def _deactivate_all_stations(self):

        """Деактивирует все станции при закрытии сервера"""

        try:

            print(" Деактивация всех станций...")

            

            # Сначала деактивируем станции с активными соединениями

            connections = self.connection_manager.get_all_connections()

            active_stations = []

            

            for fd, conn in connections.items():

                if conn.station_id and conn.box_id:

                    active_stations.append((conn.station_id, conn.box_id))

            

            if active_stations:

                print(f" Найдено {len(active_stations)} активных станций для деактивации")

                

                # Деактивируем каждую станцию

                for station_id, box_id in active_stations:

                    try:

                        # Проверяем, что пул соединений еще доступен

                        if not self.db_pool or self.db_pool._closed:

                            print(f" Пул соединений с БД уже закрыт")

                            continue

                            

                        station = await Station.get_by_id(self.db_pool, station_id)

                        if station:

                            await station.update_status(self.db_pool, "inactive")

                            print(f" Станция {box_id} (ID: {station_id}) деактивирована")

                    except Exception as e:

                        # Игнорируем ошибки с закрытым пулом соединений

                        if "Cannot acquire connection after closing pool" in str(e):

                            print(f" Пул соединений закрыт, пропускаем деактивацию станции {box_id}")

                        else:

                            print(f" Ошибка деактивации станции {box_id}: {e}")

            else:

                print(" Активных станций не найдено")

            

            await self._deactivate_all_active_stations_in_db()

                

        except Exception as e:

            print(f" Ошибка при деактивации станций: {e}")

    

    async def _close_all_connections(self):

        """Принудительно закрывает все TCP соединения"""

        try:

            print(" Принудительное закрытие всех TCP соединений...")

            

            connections = self.connection_manager.get_all_connections()

            if not connections:

                return

            

            print(f" Найдено {len(connections)} соединений для закрытия")

            

            closed_count = 0

            for fd, conn in connections.items():

                try:

                    if conn.writer and not conn.writer.is_closing():

                        print(f" Закрываем соединение {conn.addr} (станция: {conn.box_id})")

                        conn.writer.close()

                        await conn.writer.wait_closed()

                        closed_count += 1

                    else:

                        print(f" Соединение {conn.addr} уже закрыто")

                except Exception as e:

                    print(f" Ошибка закрытия соединения {conn.addr}: {e}")

            

            print(f" Закрыто {closed_count} соединений")

            

            # Очищаем менеджер соединений

            self.connection_manager.clear_all_connections()

            print(" Менеджер соединений очищен")

            

        except Exception as e:

            print(f" Ошибка при закрытии соединений: {e}")

    

    async def _deactivate_all_active_stations_in_db(self):

        """Деактивирует все станции со статусом 'active' в базе данных"""

        try:

            print(" Деактивация всех активных станций в БД...")

            

            # Проверяем, что пул соединений еще доступен

            if not self.db_pool or self.db_pool._closed:

                print(" Пул соединений с БД уже закрыт")

                return

            

            async with self.db_pool.acquire() as conn:

                async with conn.cursor() as cur:

                    # Получаем все активные станции

                    await cur.execute("SELECT station_id, box_id FROM station WHERE status = 'active'")

                    active_stations = await cur.fetchall()

                    

                    if active_stations:

                        print(f" Найдено {len(active_stations)} активных станций в БД")

                        

                        # Деактивируем все активные станции

                        await cur.execute("UPDATE station SET status = 'inactive' WHERE status = 'active'")

                        affected_rows = cur.rowcount

                        

                        print(f" Деактивировано {affected_rows} станций в БД")

                        

                        # Выводим информацию о деактивированных станциях

                        for station_id, box_id in active_stations:

                            print(f"  - Станция {box_id} (ID: {station_id})")

                    else:

                        print(" Активных станций в БД не найдено")

                        

        except Exception as e:

            if "Cannot acquire connection after closing pool" in str(e):

                print(" Пул соединений закрыт, пропускаем деактивацию станций в БД")

            else:

                print(f" Ошибка при деактивации станций в БД: {e}")





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


