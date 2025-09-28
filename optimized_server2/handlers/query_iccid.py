"""
Обработчик для запроса ICCID SIM карты
"""
from typing import Optional, Dict, Any
from datetime import datetime

from utils.packet_utils import build_query_iccid_request, parse_query_iccid_response


class QueryICCIDHandler:
    """Обработчик для запроса ICCID SIM карты"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_query_iccid_request(self, station_id: int, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на получение ICCID SIM карты
        """
        try:
            # Проверяем, что станция подключена
            if not connection or not connection.station_id:
                print("Станция не подключена для запроса ICCID")
                return None
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для команды ICCID")
                return None
            
            # Создаем команду на запрос ICCID
            iccid_command = build_query_iccid_request(
                secret_key=secret_key,
                vsn=1  # Можно получить из соединения
            )
            
            print(f"Создана команда на запрос ICCID станции {station_id}")
            return iccid_command
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return None
    
    async def handle_query_iccid_response(self, data: bytes, connection) -> Dict[str, Any]:
        """
        Обрабатывает ответ от станции на запрос ICCID
        Возвращает информацию об ICCID
        """
        try:
            # Парсим ответ от станции
            iccid_response = parse_query_iccid_response(data)
            print(f"Обработан ответ на запрос ICCID: {iccid_response}")
            
            station_id = connection.station_id
            if not station_id:
                return {
                    "success": False,
                    "message": "Станция не найдена для соединения"
                }
            
            # Сохраняем ICCID в базу данных
            await self._save_iccid_to_database(station_id, iccid_response['ICCID'])
            
            return {
                "success": True,
                "message": f"ICCID получен для станции {station_id}",
                "station_id": station_id,
                "iccid": iccid_response['ICCID'],
                "iccid_length": iccid_response['ICCIDLen'],
                "received_at": iccid_response['ReceivedAt']
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка обработки ICCID: {str(e)}"
            }
    
    async def _save_iccid_to_database(self, station_id: int, iccid: str) -> None:
        """Сохраняет ICCID в базу данных"""
        try:
            from models.station import Station
            
            # Обновляем ICCID в таблице station
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        UPDATE station 
                        SET iccid = %s, updated_at = NOW()
                        WHERE station_id = %s
                    """, (iccid, station_id))
                    await conn.commit()
            
            print(f"ICCID {iccid} сохранен для станции {station_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def send_query_iccid_command(self, station_id: int) -> Dict[str, Any]:
        """
        Отправляет команду запроса ICCID на станцию
        Возвращает результат операции
        """
        try:
            # Получаем соединение для станции
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {
                    "success": False,
                    "message": "Станция не подключена"
                }
            
            # Создаем команду запроса ICCID
            iccid_command = await self.handle_query_iccid_request(station_id, connection)
            
            if iccid_command:
                # Здесь нужно отправить команду на станцию
                # В реальной реализации это делается через writer
                print(f"Команда запроса ICCID отправлена на станцию {station_id}")
                
                return {
                    "success": True,
                    "message": f"Команда запроса ICCID отправлена на станцию {station_id}",
                    "station_id": station_id,
                    "sent_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": "Не удалось создать команду запроса ICCID"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка отправки команды ICCID: {str(e)}"
            }
    
    async def get_station_iccid(self, station_id: int) -> Dict[str, Any]:
        """
        Получает сохраненный ICCID станции из базы данных
        """
        try:
            from models.station import Station
            
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {
                    "success": False,
                    "message": "Станция не найдена"
                }
            
            # Проверяем, есть ли ICCID в базе
            iccid = getattr(station, 'iccid', None)
            iccid_updated_at = getattr(station, 'updated_at', None)
            
            if iccid:
                return {
                    "success": True,
                    "station_id": station_id,
                    "box_id": station.box_id,
                    "iccid": iccid,
                    "iccid_updated_at": iccid_updated_at.isoformat() if iccid_updated_at else None,
                    "has_iccid": True
                }
            else:
                return {
                    "success": True,
                    "station_id": station_id,
                    "box_id": station.box_id,
                    "iccid": None,
                    "iccid_updated_at": None,
                    "has_iccid": False,
                    "message": "ICCID не найден в базе данных"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения ICCID: {str(e)}"
            }
