"""
Обработчик команды перезагрузки кабинета
"""
import asyncio
from typing import Optional
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from models.connection import StationConnection
from utils.packet_utils import build_restart_cabinet_request, parse_restart_cabinet_response


class RestartCabinetHandler:
    """Обработчик для команды перезагрузки кабинета"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('restartcabinethandler')
    
    async def send_restart_command(self, station_id: int, admin_user_id: int) -> dict:
        """
        Отправляет команду перезагрузки кабинета на станцию
        """
        try:
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {
                    "success": False,
                    "error": f"Станция с ID {station_id} не найдена"
                }
            
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
            
            # Создаем пакет команды перезагрузки
            restart_packet = build_restart_cabinet_request(connection.secret_key, vsn=1)
            
            
            # Отправляем команду
            if not connection.writer or connection.writer.is_closing():
                return {
                    "success": False,
                    "error": f"Соединение со станцией {station.box_id} недоступно"
                }
            
            connection.writer.write(restart_packet)
            await connection.writer.drain()
            
            # Меняем статус станции на inactive
            await station.update_status(self.db_pool, "inactive")
            
            # Логируем отправку команды в файл
            self.logger.info(f"Команда перезагрузки отправлена на станцию {station.box_id} (ID: {station_id}) | "
                           f"Админ: {admin_user_id} | Статус изменен на inactive")
            
            return {
                "success": True,
                "message": f"Команда перезагрузки отправлена на станцию {station.box_id}",
                "station_box_id": station.box_id,
                "packet_hex": restart_packet.hex().upper()
            }
            
        except Exception as e:
            error_msg = f"Ошибка отправки команды перезагрузки: {str(e)}"
            
            # Логируем ошибку в файл
            self.logger.error(f"Ошибка отправки команды перезагрузки на станцию {station_id} | "
                            f"Админ: {admin_user_id} | Ошибка: {str(e)}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def handle_restart_response(self, data: bytes, connection: StationConnection) -> Optional[bytes]:
        """
        Обрабатывает ответ на команду перезагрузки от станции
        """
        try:
            # Парсим ответ
            response = parse_restart_cabinet_response(data)
            
            if response.get("CheckSumValid", False):
                # Логируем получение ответа в файл
                self.logger.info(f"Получен ответ на команду перезагрузки от станции {connection.box_id} (ID: {connection.station_id}) | "
                               f"Ответ: {response}")
            
           
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
