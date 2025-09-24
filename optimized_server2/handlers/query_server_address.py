"""
Обработчик команды запроса адреса сервера
"""
import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone

from models.station import Station
from utils.packet_utils import build_query_server_address_request, parse_query_server_address_response
from models.connection import StationConnection


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
        Отправляет запрос на получение адреса сервера станции.
        """
        station = await Station.get_by_id(self.db_pool, station_id)
        if not station:
            self.logger.error(f"Станция с ID {station_id} не найдена для запроса адреса сервера.")
            return {"success": False, "message": "Станция не найдена."}

        connection = self.connection_manager.get_connection_by_station_id(station_id)
        if not connection or not connection.writer or connection.writer.is_closing():
            self.logger.error(f"Соединение со станцией {station.box_id} (ID: {station_id}) неактивно для запроса адреса сервера.")
            return {"success": False, "message": "Станция не подключена или соединение неактивно."}

        secret_key = connection.secret_key
        if not secret_key:
            self.logger.error(f"Секретный ключ для станции {station.box_id} (ID: {station_id}) не найден.")
            return {"success": False, "message": "Секретный ключ не найден."}

        try:
            server_address_request_packet = build_query_server_address_request(secret_key, vsn=1)
            packet_hex = server_address_request_packet.hex()

            connection.writer.write(server_address_request_packet)
            await connection.writer.drain()

            self.logger.info(f"Запрос адреса сервера отправлен на станцию {station.box_id} (ID: {station_id}) | Пакет: {packet_hex}")
            print(f" Запрос адреса сервера отправлен на станцию {station.box_id} (ID: {station_id})")

            return {
                "success": True,
                "message": f"Запрос адреса сервера отправлен на станцию {station.box_id}.",
                "packet_hex": packet_hex
            }
        except Exception as e:
            self.logger.error(f"Ошибка отправки запроса адреса сервера на станцию {station.box_id} (ID: {station_id}): {e}")
            return {"success": False, "message": f"Ошибка отправки запроса адреса сервера: {e}"}

    async def handle_query_server_address_response(self, data: bytes, connection: StationConnection) -> None:
        """
        Обрабатывает ответ на запрос адреса сервера от станции
        НЕ сохраняет данные в БД, передает напрямую фронтенду
        """
        try:
            # Парсим ответ
            response = parse_query_server_address_response(data)
            
            if not response.get("CheckSumValid", False):
                print(f" Получен некорректный ответ на запрос адреса сервера от станции {connection.box_id}")
                return
            
            print(f" Получен ответ на запрос адреса сервера от станции {connection.box_id}")
            print(f" Адрес сервера: {response.get('Address', 'N/A')}")
            print(f" Порт сервера: {response.get('Ports', 'N/A')}")
            print(f" Интервал heartbeat: {response.get('Heartbeat', 'N/A')}")
            
            # Сохраняем данные адреса сервера в кэш соединения
            connection.server_address_cache = {
                'address': response.get('Address', 'N/A'),
                'ports': response.get('Ports', 'N/A'),
                'heartbeat': response.get('Heartbeat', 'N/A'),
                'last_update': datetime.now(timezone.utc).isoformat()
            }
            
            print(f" Адрес сервера станции {connection.box_id} сохранен в кэш")
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос адреса сервера от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Адрес: {response.get('Address', 'N/A')} | Порт: {response.get('Ports', 'N/A')} | "
                           f"Heartbeat: {response.get('Heartbeat', 'N/A')}")
            
        except Exception as e:
            print(f" Ошибка обработки ответа на запрос адреса сервера: {e}")
            self.logger.error(f"Ошибка обработки ответа на запрос адреса сервера от станции {connection.box_id}: {e}")

    async def get_station_server_address(self, station_id: int) -> dict:
        """
        Получает адрес сервера станции из кэша соединения
        """
        try:
            # Получаем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {
                    "success": False,
                    "error": "Станция не подключена"
                }
            
            # Проверяем, есть ли кэш адреса сервера
            if hasattr(connection, 'server_address_cache') and connection.server_address_cache:
                return {
                    "success": True,
                    "server_address": connection.server_address_cache
                }
            else:
                return {
                    "success": False,
                    "error": "Адрес сервера не загружен. Отправьте запрос адреса сервера."
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка получения адреса сервера: {str(e)}"
            }