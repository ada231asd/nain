"""
Обработчик команды установки адреса сервера
"""
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from utils.packet_utils import build_set_server_address_request, parse_set_server_address_response


class SetServerAddressHandler:
    """Обработчик для команды установки адреса сервера"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('setserveraddresshandler')
    
    async def send_set_server_address_request(self, station_id: int, server_address: str, server_port: str, heartbeat_interval: int = 30) -> dict:
        """
        Отправляет запрос установки адреса сервера на станцию
        """
        try:
            
            if not server_address or not server_port:
                return {
                    "success": False,
                    "error": "Адрес сервера и порт не могут быть пустыми"
                }
            
            if not (1 <= heartbeat_interval <= 255):
                return {
                    "success": False,
                    "error": f"Интервал heartbeat должен быть от 1 до 255, получен: {heartbeat_interval}"
                }
            
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
            
            # Создаем пакет установки адреса сервера
            set_address_packet = build_set_server_address_request(
                connection.secret_key, 
                server_address, 
                server_port, 
                heartbeat_interval, 
                vsn=1
            )
            
            
            # Отправляем команду
            if not connection.writer or connection.writer.is_closing():
                return {
                    "success": False,
                    "error": f"Соединение со станцией {station.box_id} недоступно"
                }
            
            connection.writer.write(set_address_packet)
            await connection.writer.drain()
            
            # Логируем отправку команды в файл
            self.logger.info(f"Установка адреса сервера отправлена на станцию {station.box_id} (ID: {station_id}) | "
                           f"Адрес: {server_address}:{server_port} | Heartbeat: {heartbeat_interval}")
            
            return {
                "success": True,
                "message": f"Установка адреса сервера {server_address}:{server_port} отправлена на станцию {station.box_id}"
            }
            
        except Exception as e:
            error_msg = f"Ошибка отправки установки адреса сервера: {str(e)}"
            
            # Логируем ошибку в файл
            self.logger.error(f"Ошибка установки адреса сервера на станцию {station_id} | "
                            f"Адрес: {server_address}:{server_port} | Ошибка: {str(e)}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def handle_set_server_address_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ на установку адреса сервера от станции
        """
        try:
            # Парсим ответ
            response = parse_set_server_address_response(data)
            
            if not response.get("CheckSumValid", False):
                return
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на установку адреса сервера от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Статус: Успешно, станция перезагружается")
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            self.logger.error(f"Ошибка обработки ответа на установку адреса сервера от станции {connection.box_id}: {e}")

