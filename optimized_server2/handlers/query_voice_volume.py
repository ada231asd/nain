"""
Обработчик команды запроса уровня громкости голосового вещания
"""
from datetime import datetime
from utils.packet_utils import get_moscow_time

from models.station import Station
from utils.packet_utils import build_query_voice_volume_request, parse_query_voice_volume_response
from utils.centralized_logger import get_logger


class QueryVoiceVolumeHandler:
    """Обработчик для команды запроса уровня громкости голосового вещания"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('query_voice_volume')
    
    async def send_voice_volume_request(self, station_id: int) -> dict:
        """
        Отправляет запрос уровня громкости на станцию
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
            
            # Создаем пакет запроса громкости
            voice_volume_packet = build_query_voice_volume_request(connection.secret_key, vsn=1)
            
            # Выводим информацию о пакете для отладки
            packet_hex = voice_volume_packet.hex().upper()
            print(f" Отправляем запрос уровня громкости на станцию {station.box_id}")
            print(f" Пакет команды (0x77): {packet_hex}")
            print(f" Размер пакета: {len(voice_volume_packet)} байт")
            
            # Отправляем команду
            if not connection.writer or connection.writer.is_closing():
                return {
                    "success": False,
                    "error": f"Соединение со станцией {station.box_id} недоступно"
                }
            
            connection.writer.write(voice_volume_packet)
            await connection.writer.drain()
            
            # Логируем отправку команды в файл
            self.logger.info(f"Запрос уровня громкости отправлен на станцию {station.box_id} (ID: {station_id}) | "
                           f"Пакет: {packet_hex}")
            
            print(f"Запрос уровня громкости отправлен на станцию {station.box_id} (ID: {station_id})")
            
            return {
                "success": True,
                "message": f"Запрос уровня громкости отправлен на станцию {station.box_id}",
                "station_box_id": station.box_id,
                "packet_hex": packet_hex
            }
            
        except Exception as e:
            error_msg = f"Ошибка отправки запроса уровня громкости: {str(e)}"
            print(error_msg)
            
            # Логируем ошибку в файл
            self.logger.error(f"Ошибка отправки запроса уровня громкости на станцию {station_id} | "
                            f"Ошибка: {str(e)}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def handle_voice_volume_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ на запрос уровня громкости от станции
        """
        try:
            # Парсим ответ
            response = parse_query_voice_volume_response(data)
            
            if not response.get("CheckSumValid", False) or response.get("Error"):
                print(f" Получен некорректный ответ на запрос уровня громкости от станции {connection.box_id}: {response.get('Error', 'Неверный checksum')}")
                self.logger.error(f"Неверный ответ уровня громкости от станции {connection.box_id}: {response.get('Error', 'Неверный checksum')}")
                return
            
            # Выводим детальную информацию об ответе
            volume_level = response.get('VolumeLevel', 'N/A')
            packet_len = response.get('PacketLen', 'N/A')
            vsn = response.get('VSN', 'N/A')
            checksum = response.get('CheckSum', 'N/A')
            token = response.get('Token', 'N/A')
            raw_packet = response.get('RawPacket', 'N/A')
            
            print(f" Получен ответ на запрос уровня громкости от станции {connection.box_id}")
            print(f" Пакет ответа (0x77): {raw_packet}")
            print(f" Размер пакета: {packet_len} байт")
            print(f" Уровень громкости: {volume_level}")
            print(f" VSN: {vsn}")
            print(f" CheckSum: {checksum}")
            print(f" Token: {token}")
            
            print(f" Уровень громкости станции {connection.box_id} получен")
            
            # Сохраняем данные уровня громкости в объект соединения для передачи на фронтенд
            connection.voice_volume_data = {
                'volume_level': volume_level,
                'volume_percentage': int(volume_level) * 10 if volume_level != 'N/A' else 0,
                'last_update': get_moscow_time().isoformat(),
                'packet_hex': raw_packet,
                'vsn': vsn,
                'checksum': checksum,
                'token': token
            }
            
            # Логируем получение ответа в файл
            self.logger.info(f"Получен ответ на запрос уровня громкости от станции {connection.box_id} (ID: {connection.station_id}) | "
                           f"Уровень громкости: {volume_level} | Пакет: {raw_packet}")
            
        except Exception as e:
            print(f" Ошибка обработки ответа на запрос уровня громкости от станции {connection.box_id}: {e}")
            self.logger.error(f"Ошибка обработки ответа на запрос уровня громкости от станции {connection.box_id}: {e}")

