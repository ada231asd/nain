"""
Обработчик команды установки уровня громкости голосового вещания
"""
from datetime import datetime

from utils.centralized_logger import get_logger
from models.station import Station
from utils.packet_utils import build_set_voice_volume_request, parse_set_voice_volume_response


class SetVoiceVolumeHandler:
    """Обработчик для команды установки уровня громкости голосового вещания"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('setvoicevolumehandler')
    
    async def send_set_voice_volume_request(self, station_id: int, volume_level: int) -> dict:
        """
        Отправляет запрос установки уровня громкости на станцию
        Возвращает результат операции
        """
        try:
            # Проверяем корректность уровня громкости
            if not (0 <= volume_level <= 15):
                return {
                    "success": False,
                    "error": f"Уровень громкости должен быть от 0 до 15, получен: {volume_level}"
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
            
            # Создаем пакет установки громкости
            set_volume_packet = build_set_voice_volume_request(connection.secret_key, volume_level, vsn=1)
            
            # Выводим информацию о пакете для отладки
            packet_hex = set_volume_packet.hex().upper()
            print(f" Отправляем установку уровня громкости на станцию {station.box_id}")
            print(f" Пакет команды (0x70): {packet_hex}")
            print(f" Размер пакета: {len(set_volume_packet)} байт")
            print(f" Уровень громкости: {volume_level}")
            
            # Отправляем команду
            if not connection.writer or connection.writer.is_closing():
                return {
                    "success": False,
                    "error": f"Соединение со станцией {station.box_id} недоступно"
                }
            
            connection.writer.write(set_volume_packet)
            await connection.writer.drain()
            
            # Логируем отправку команды в файл
            self.logger.info(f"Установка уровня громкости отправлена на станцию {station.box_id} (ID: {station_id}) | "
                           f"Уровень: {volume_level} | Пакет: {packet_hex}")
            
            print(f"Установка уровня громкости отправлена на станцию {station.box_id} (ID: {station_id})")
            
            return {
                "success": True,
                "message": f"Установка уровня громкости {volume_level} отправлена на станцию {station.box_id}",
                "station_box_id": station.box_id,
                "volume_level": volume_level,
                "packet_hex": packet_hex
            }
            
        except Exception as e:
            error_msg = f"Ошибка отправки установки уровня громкости: {str(e)}"
            print(error_msg)
            
            # Логируем ошибку в файл
            self.logger.error(f"Ошибка установки уровня громкости на станцию {station_id} | "
                            f"Уровень: {volume_level} | Ошибка: {str(e)}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def handle_set_voice_volume_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ на установку уровня громкости от станции
        """
        try:
            # Парсим ответ
            response = parse_set_voice_volume_response(data)
            
            if not response.get("CheckSumValid", False):
                print(f"Получен некорректный ответ на установку уровня громкости от станции {connection.box_id}")
                return
            
            print(f" Получен ответ на установку уровня громкости от станции {connection.box_id}")
            print(f" Установка громкости выполнена успешно")
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на установку уровня громкости от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Статус: Успешно")
            
        except Exception as e:
            print(f"Ошибка обработки ответа на установку уровня громкости: {e}")
            self.logger.error(f"Ошибка обработки ответа на установку уровня громкости от станции {connection.box_id}: {e}")

