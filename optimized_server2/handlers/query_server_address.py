"""
Обработчик команды запроса адреса сервера
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any

from models.station import Station
from utils.packet_utils import build_query_server_address_request, parse_query_server_address_response


class QueryServerAddressHandler:
    """Обработчик для команды запроса адреса сервера (0x6A)"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Настраивает логгер для записи в файл"""
        os.makedirs('logs', exist_ok=True)
        logger = logging.getLogger('query_server_address')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        handler = logging.FileHandler('logs/query_server_address.log', encoding='utf-8')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    async def send_query_server_address_request(self, station_id: int) -> Dict[str, Any]:
        """
        Отправляет запрос адреса сервера на станцию
        Возвращает результат операции
        """
        try:
            # Получаем станцию из БД
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {
                    "success": False,
                    "error": f"Станция с ID {station_id} не найдена"
                }
            
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {
                    "success": False,
                    "error": f"Станция {station.box_id} не подключена"
                }
            
            if not connection.secret_key:
                return {
                    "success": False,
                    "error": f"Нет секретного ключа для станции {station.box_id}"
                }
            
            # Создаем пакет запроса адреса сервера
            query_address_packet = build_query_server_address_request(connection.secret_key, vsn=1)
            packet_hex = query_address_packet.hex()
            
            # Отправляем команду
            if not connection.writer or connection.writer.is_closing():
                return {
                    "success": False,
                    "error": f"Соединение со станцией {station.box_id} недоступно"
                }
            
            connection.writer.write(query_address_packet)
            await connection.writer.drain()
            
            self.logger.info(f"Запрос адреса сервера отправлен на станцию {station.box_id} (ID: {station_id}) | Пакет: {packet_hex}")
            print(f" Запрос адреса сервера отправлен на станцию {station.box_id} (ID: {station_id})")
            
            return {
                "success": True,
                "message": f"Запрос адреса сервера отправлен на станцию {station.box_id}",
                "station_box_id": station.box_id,
                "packet_hex": packet_hex
            }
            
        except Exception as e:
            error_msg = f"Ошибка отправки запроса адреса сервера: {str(e)}"
            print(error_msg)
            self.logger.error(f"Ошибка отправки запроса адреса сервера на станцию {station_id}: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def handle_query_server_address_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ на запрос адреса сервера от станции
        Сохраняет данные в базу данных
        """
        try:
            # Парсим ответ
            response = parse_query_server_address_response(data)
            
            if not response.get("CheckSumValid", False):
                print(f" Получен некорректный ответ на запрос адреса сервера от станции {connection.box_id}")
                self.logger.error(f"Неверный ответ адреса сервера от станции {connection.box_id}: Неверный checksum")
                return
            
            # Выводим детальную информацию об ответе
            address = response.get('Address', 'N/A')
            ports = response.get('Ports', 'N/A')
            heartbeat = response.get('Heartbeat', 'N/A')
            packet_len = response.get('PacketLen', 'N/A')
            vsn = response.get('VSN', 'N/A')
            checksum = response.get('CheckSum', 'N/A')
            token = response.get('Token', 'N/A')
            raw_packet = response.get('RawPacket', 'N/A')
            
            print(f" Получен ответ на запрос адреса сервера от станции {connection.box_id}")
            print(f" Пакет ответа (0x6A): {raw_packet}")
            print(f" Размер пакета: {packet_len} байт")
            print(f" Адрес сервера: {address}")
            print(f" Порт сервера: {ports}")
            print(f" Интервал heartbeat: {heartbeat}")
            print(f" VSN: {vsn}")
            print(f" CheckSum: {checksum}")
            print(f" Token: {token}")
            
            # Сохраняем адрес сервера в базу данных
            await self._save_server_address_to_database(
                connection.station_id, 
                address, 
                ports, 
                heartbeat
            )
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос адреса сервера от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Адрес: {address}:{ports} | Heartbeat: {heartbeat} | Пакет: {raw_packet}")
            
        except Exception as e:
            print(f" Ошибка обработки ответа на запрос адреса сервера: {e}")
            self.logger.error(f"Ошибка обработки ответа на запрос адреса сервера от станции {connection.box_id}: {e}")
    
    async def _save_server_address_to_database(self, station_id: int, address: str, ports: str, heartbeat: int) -> None:
        """Сохраняет адрес сервера в базу данных"""
        try:
            # Обновляем адрес сервера в таблице station
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        UPDATE station 
                        SET server_address = %s, server_ports = %s, heartbeat_interval = %s, 
                            server_address_updated_at = NOW()
                        WHERE station_id = %s
                    """, (address, ports, heartbeat, station_id))
                    await conn.commit()
            
            print(f" Адрес сервера {address}:{ports} (heartbeat: {heartbeat}) сохранен для станции {station_id}")
            
        except Exception as e:
            print(f" Ошибка сохранения адреса сервера в БД: {e}")
            self.logger.error(f"Ошибка сохранения адреса сервера в БД для станции {station_id}: {e}")
    
    async def get_station_server_address(self, station_id: int) -> Dict[str, Any]:
        """
        Получает сохраненный адрес сервера станции из базы данных
        """
        try:
            # Получаем станцию из БД
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {
                    "success": False,
                    "error": f"Станция с ID {station_id} не найдена"
                }
            
            # Проверяем, есть ли адрес сервера в базе
            server_address = getattr(station, 'server_address', None)
            server_ports = getattr(station, 'server_ports', None)
            heartbeat_interval = getattr(station, 'heartbeat_interval', None)
            server_address_updated_at = getattr(station, 'server_address_updated_at', None)
            
            if server_address:
                return {
                    "success": True,
                    "station_id": station_id,
                    "box_id": station.box_id,
                    "server_address": server_address,
                    "server_ports": server_ports,
                    "heartbeat_interval": heartbeat_interval,
                    "server_address_updated_at": server_address_updated_at.isoformat() if server_address_updated_at else None,
                    "has_server_address": True
                }
            else:
                return {
                    "success": True,
                    "station_id": station_id,
                    "box_id": station.box_id,
                    "server_address": None,
                    "server_ports": None,
                    "heartbeat_interval": None,
                    "server_address_updated_at": None,
                    "has_server_address": False,
                    "message": "Адрес сервера не найден в базе данных"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка получения адреса сервера: {str(e)}"
            }
