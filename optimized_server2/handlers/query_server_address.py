"""
Обработчик команды запроса адреса сервера
"""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from models.station import Station
from utils.packet_utils import build_query_server_address_request, parse_query_server_address_response, get_moscow_time
from models.connection import StationConnection
from utils.centralized_logger import get_logger


class QueryServerAddressHandler:
    """Обработчик для команды запроса адреса сервера (0x6A)"""

    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('query_server_address')

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
            
            print(f" Адрес сервера станции {connection.box_id} получен")
            
            # Сохраняем данные адреса сервера в объект соединения для передачи на фронтенд
            connection.server_address_data = {
                'address': response.get('Address', 'N/A'),
                'port': response.get('Ports', 'N/A'),
                'heartbeat_interval': response.get('Heartbeat', 'N/A'),
                'last_update': get_moscow_time().isoformat(),
                'packet_hex': response.get('RawPacket', 'N/A'),
                'vsn': response.get('VSN', 'N/A'),
                'checksum': response.get('CheckSum', 'N/A'),
                'token': response.get('Token', 'N/A')
            }
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос адреса сервера от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Адрес: {response.get('Address', 'N/A')} | Порт: {response.get('Ports', 'N/A')} | "
                           f"Heartbeat: {response.get('Heartbeat', 'N/A')}")
            
        except Exception as e:
            print(f" Ошибка обработки ответа на запрос адреса сервера: {e}")
            self.logger.error(f"Ошибка обработки ответа на запрос адреса сервера от станции {connection.box_id}: {e}")
