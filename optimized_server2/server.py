"""
Оптимизированный сервер с TCP и HTTP серверами
"""
import asyncio
import signal
import sys
from typing import Optional

import aiomysql
from aiohttp import web

from config.settings import SERVER_IP, TCP_PORT, HTTP_PORT, DB_CONFIG, CONNECTION_TIMEOUT
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
# from utils.packet_logger import packet_logger  # Удален
from utils.packet_utils import parse_packet
from utils.station_resolver import StationResolver


class OptimizedServer:
    """Оптимизированный сервер с TCP и HTTP"""
    
    def __init__(self):
        self.db_pool: Optional[aiomysql.Pool] = None
        self.connection_manager = ConnectionManager()
        self.station_resolver = StationResolver(self.connection_manager)
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
        self.tcp_server: Optional[asyncio.Server] = None
        self.http_server: Optional[HTTPServer] = None
        self.running = False
    
    async def initialize_database(self):
        """Инициализирует подключение к базе данных"""
        try:
            self.db_pool = await aiomysql.create_pool(**DB_CONFIG)
            print("Подключение к базе данных установлено")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            sys.exit(1)
    
    async def cleanup_database(self):
        """Закрывает подключение к базе данных"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            print("Подключение к базе данных закрыто")
    
    async def send_command_to_station(self, command_bytes: bytes, connection, station_info: dict) -> bool:
        """Отправляет команду на станцию через TCP соединение"""
        try:
            if connection.writer and not connection.writer.is_closing():
                # Логируем исходящий пакет
                # packet_logger.log_outgoing_packet(command_bytes, station_info, parse_packet(command_bytes))  # Удален
                # packet_logger.log_packet_human_readable(command_bytes, "outgoing", station_info, parse_packet(command_bytes))  # Удален
                connection.writer.write(command_bytes)
                await connection.writer.drain()
                return True
            else:
                print("TCP соединение со станцией недоступно")
                return False
        except Exception as e:
            print(f"Ошибка отправки команды на станцию: {e}")
            return False

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Обрабатывает подключение клиента"""
        fd = writer.transport.get_extra_info('socket').fileno()
        addr = writer.get_extra_info('peername')
        print(f"Подключен: {addr} (fd={fd})")
        
        # Создаем соединение
        connection = StationConnection(fd, addr, writer=writer)
        self.connection_manager.add_connection(connection)
        connection_reset = False
        
        try:
            while self.running:
                # Читаем данные с таймаутом
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=CONNECTION_TIMEOUT)
                    if not data:
                        break
                except asyncio.TimeoutError:
                    print(f"Таймаут соединения для {addr}")
                    break
                
                # Определяем команду
                if len(data) < 3:
                    continue
                
                command = data[2]
                response = None
                
                # Логируем входящий пакет
                station_info = {
                    "fd": fd,
                    "addr": addr,
                    "box_id": connection.box_id,
                    "station_id": connection.station_id,
                    "station_status": connection.station_status
                }
                parsed_data = parse_packet(data)
                # packet_logger.log_incoming_packet(data, station_info, parsed_data)  # Удален
                # packet_logger.log_packet_human_readable(data, "incoming", station_info, parsed_data)  # Удален
                
                try:
                    if command == 0x60:  # Login
                        response = await self.station_handler.handle_login(data, connection)
                        if response is None:
                            # Соединение должно быть закрыто
                            break
                    
                    elif command == 0x61:  # Heartbeat
                        response = await self.station_handler.handle_heartbeat(data, connection)
                    
                    elif command == 0x65:  # Borrow Power Bank
                        # Проверяем, это запрос или ответ
                        if len(data) >= 8:
                            # Это может быть запрос на выдачу (8 байт) или ответ (12+ байт)
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
                        continue
                    
                    elif command == 0x66:  # Return Power Bank
                        # Обрабатываем запрос на возврат повербанка
                        response = await self.return_handler.handle_return_request(data, connection)
                        if response:
                            writer.write(response)
                            await writer.drain()
                        continue
                    
                    elif command == 0x80:  # Force Eject Power Bank
                        # Обрабатываем ответ на принудительное извлечение
                        await self.eject_handler.handle_force_eject_response(data, connection)
                        continue
                    
                    elif command == 0x69:  # Query ICCID
                        # Обрабатываем ответ на запрос ICCID
                        iccid_result = await self.query_iccid_handler.handle_query_iccid_response(data, connection)
                        print(f"Результат запроса ICCID: {iccid_result}")
                        continue
                    
                    elif command == 0x83:  # Slot Status Abnormal Report
                        # Обрабатываем отчет об аномалии слота
                        abnormal_response = await self.slot_abnormal_report_handler.handle_slot_abnormal_report_request(data, connection)
                        if abnormal_response:
                            writer.write(abnormal_response)
                            await writer.drain()
                        continue
                    
                    elif command == 0x67:  # Restart Cabinet Response
                        # Обрабатываем ответ на команду перезагрузки кабинета
                        await self.restart_cabinet_handler.handle_restart_response(data, connection)
                        continue
                    
                    elif command == 0x64:  # Query Inventory Response
                        # Обрабатываем ответ на запрос инвентаря
                        await self.query_inventory_handler.handle_inventory_response(data, connection)
                        continue
                    
                    elif command == 0x77:  # Query Voice Volume Response
                        # Обрабатываем ответ на запрос уровня громкости
                        await self.query_voice_volume_handler.handle_voice_volume_response(data, connection)
                        continue
                    
                    elif command == 0x70:  # Set Voice Volume Response
                        # Обрабатываем ответ на установку уровня громкости
                        await self.set_voice_volume_handler.handle_set_voice_volume_response(data, connection)
                        continue
                    
                    elif command == 0x63:  # Set Server Address Response
                        # Обрабатываем ответ на установку адреса сервера
                        await self.set_server_address_handler.handle_set_server_address_response(data, connection)
                        continue
                    
                    elif command == 0x6A:  # Query Server Address Response
                        # Обрабатываем ответ на запрос адреса сервера
                        await self.query_server_address_handler.handle_query_server_address_response(data, connection)
                        continue
                    
                    else:
                        print(f"Неизвестная команда: {hex(command)}")
                        continue
                    
                    # Отправляем ответ
                    if response:
                        # Логируем исходящий пакет
                        # packet_logger.log_outgoing_packet(response, station_info, parse_packet(response))  # Удален
                        # packet_logger.log_packet_human_readable(response, "outgoing", station_info, parse_packet(response))  # Удален
                        writer.write(response)
                        await writer.drain()
                
                except Exception as e:
                    print(f"Ошибка обработки команды {hex(command)}: {e}")
                    continue
        
        except asyncio.CancelledError:
            print(f"Соединение {addr} отменено")
            raise
        except ConnectionResetError as e:
            print(f"Соединение {addr} сброшено клиентом: {e}")
            connection_reset = True
        except Exception as e:
            print(f"Ошибка в обработке клиента {addr}: {e}")
            connection_reset = False
        
        finally:
            # Закрываем соединение
            print(f"Отключен: {addr} (fd={fd})")
            self.connection_manager.remove_connection(fd)
            
            # Безопасное закрытие соединения
            try:
                if not writer.is_closing():
                    writer.close()
                    # Не ждем wait_closed() для сброшенных соединений
                    if not connection_reset:
                        try:
                            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                        except asyncio.TimeoutError:
                            print(f"Таймаут при закрытии соединения {addr}")
                        except Exception as wait_error:
                            if not isinstance(wait_error, (ConnectionResetError, OSError)):
                                print(f"Ошибка ожидания закрытия соединения {addr}: {wait_error}")
            except Exception as close_error:
                # Игнорируем ошибки закрытия для сброшенных соединений
                if not isinstance(close_error, (ConnectionResetError, OSError)):
                    print(f"Ошибка при закрытии соединения {addr}: {close_error}")
    
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
            
            # Запускаем TCP сервер
            self.tcp_server = await asyncio.start_server(
                self.handle_client,
                SERVER_IP,
                TCP_PORT
            )
            
            # Запускаем HTTP сервер с connection_manager
            http_app = self.http_server.create_app(self.connection_manager)
            http_runner = web.AppRunner(http_app)
            await http_runner.setup()
            http_site = web.TCPSite(http_runner, '0.0.0.0', HTTP_PORT)
            await http_site.start()
            
            self.running = True
            print(f"TCP сервер запущен на {SERVER_IP}:{TCP_PORT}")
            print(f"HTTP сервер запущен на 0.0.0.0:{HTTP_PORT}")
            print("Доступные HTTP endpoints:")
            print("  POST /api/auth/register - Регистрация пользователя (отправляет пароль на email)")
            print("  POST /api/auth/login - Авторизация по паролю")
            print("  GET /api/auth/profile - Получение профиля пользователя")
            print("  PUT /api/auth/profile - Обновление профиля пользователя")
            
            # Запускаем мониторинг соединений
            asyncio.create_task(self._connection_monitor())
            
            # Ждем завершения серверов
            async with self.tcp_server:
                await self.tcp_server.serve_forever()
        
        except Exception as e:
            print(f"Ошибка запуска серверов: {e}")
        finally:
            # База данных будет закрыта в stop_servers()
            pass
    
    async def _connection_monitor(self):
        """Мониторинг соединений"""
        while self.running:
            try:
                # Очищаем неактивные соединения
                cleaned = self.connection_manager.cleanup_inactive_connections(CONNECTION_TIMEOUT)
                if cleaned > 0:
                    print(f"Очищено {cleaned} неактивных соединений")
                
                # Выводим статистику соединений
                connections = self.connection_manager.get_all_connections()
                if connections:
                    print(f"Активных соединений: {len(connections)}")
                    
                    # Группируем по станциям для выявления дублирования
                    stations = {}
                    for fd, conn in connections.items():
                        if conn.station_id:
                            if conn.station_id not in stations:
                                stations[conn.station_id] = []
                            stations[conn.station_id].append((fd, conn))
                    
                    # Выводим информацию о станциях
                    for station_id, station_connections in stations.items():
                        if len(station_connections) > 1:
                            print(f"    Станция {station_id} имеет {len(station_connections)} соединений:")
                            for fd, conn in station_connections:
                                print(f"    fd={fd} | BoxID={conn.box_id} | Status={conn.station_status}")
                        else:
                            fd, conn = station_connections[0]
                            print(f"  fd={fd} | BoxID={conn.box_id} | Status={conn.station_status}")
                    
                    # Очищаем дублирующиеся соединения
                    for station_id, station_connections in stations.items():
                        if len(station_connections) > 1:
                            print(f"Очищаем дублирующиеся соединения для станции {station_id}")
                            # Оставляем только самое новое соединение
                            station_connections.sort(key=lambda x: x[1].last_heartbeat, reverse=True)
                            for fd, conn in station_connections[1:]:  # Удаляем все кроме первого
                                print(f"Закрываем дублирующееся соединение fd={fd}")
                                self.connection_manager.close_connection(fd)
                
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
            except Exception as e:
                print(f"Ошибка в мониторинге соединений: {e}")
                await asyncio.sleep(30)
    
    async def stop_servers(self):
        """Останавливает серверы"""
        print("Остановка серверов...")
        self.running = False
        
        # Деактивируем все станции перед закрытием
        await self._deactivate_all_stations()
        
        if self.tcp_server:
            self.tcp_server.close()
        if self.http_server:
            self.http_server.stop_server()
        
        # Закрываем базу данных после деактивации станций
        await self.cleanup_database()
    
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
                print(f"📡 Найдено {len(active_stations)} активных станций для деактивации")
                
                # Деактивируем каждую станцию
                for station_id, box_id in active_stations:
                    try:
                        # Проверяем, что пул соединений еще доступен
                        if not self.db_pool or self.db_pool._closed:
                            print(f" Пул соединений с БД уже закрыт, пропускаем деактивацию станции {box_id}")
                            continue
                            
                        station = await Station.get_by_id(self.db_pool, station_id)
                        if station:
                            await station.update_status(self.db_pool, "inactive")
                            print(f" Станция {box_id} (ID: {station_id}) деактивирована")
                    except Exception as e:
                        print(f" Ошибка деактивации станции {box_id}: {e}")
            else:
                print("📡 Активных станций не найдено")
            
            # Дополнительно деактивируем все станции со статусом 'active' в БД
            await self._deactivate_all_active_stations_in_db()
                
        except Exception as e:
            print(f" Ошибка при деактивации станций: {e}")
    
    async def _deactivate_all_active_stations_in_db(self):
        """Деактивирует все станции со статусом 'active' в базе данных"""
        try:
            print(" Деактивация всех активных станций в БД...")
            
            # Проверяем, что пул соединений еще доступен
            if not self.db_pool or self.db_pool._closed:
                print(" Пул соединений с БД уже закрыт, пропускаем деактивацию станций в БД")
                return
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем все активные станции
                    await cur.execute("SELECT station_id, box_id FROM station WHERE status = 'active'")
                    active_stations = await cur.fetchall()
                    
                    if active_stations:
                        print(f"📡 Найдено {len(active_stations)} активных станций в БД")
                        
                        # Деактивируем все активные станции
                        await cur.execute("UPDATE station SET status = 'inactive' WHERE status = 'active'")
                        affected_rows = cur.rowcount
                        
                        print(f" Деактивировано {affected_rows} станций в БД")
                        
                        # Выводим информацию о деактивированных станциях
                        for station_id, box_id in active_stations:
                            print(f"  - Станция {box_id} (ID: {station_id})")
                    else:
                        print("📡 Активных станций в БД не найдено")
                        
        except Exception as e:
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
        # На Windows используем другой подход
        def windows_signal_handler(signum, frame):
            signal_handler()
        
        signal.signal(signal.SIGINT, windows_signal_handler)
        signal.signal(signal.SIGTERM, windows_signal_handler)
    
    try:
        await server.start_servers()
    except KeyboardInterrupt:
        print("Получен сигнал прерывания")
    finally:
        await server.stop_servers()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Серверы остановлены")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)
