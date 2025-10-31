"""
API для запроса инвентаря кабинета
"""
from aiohttp import web
from aiohttp.web import Application
import aiomysql

from handlers.query_inventory import QueryInventoryHandler
from utils.centralized_logger import get_logger
from models.station import Station
from utils.auth_middleware import jwt_middleware

class QueryInventoryAPI:
    """API для запроса инвентаря кабинета"""

    def __init__(self, db_pool: aiomysql.Pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.query_inventory_handler = QueryInventoryHandler(db_pool, connection_manager)
        self.logger = get_logger('queryinventoryapi')

    @jwt_middleware
    async def query_inventory(self, request: web.Request):
        """
        Отправляет запрос на получение инвентаря станции.
        POST /api/query-inventory
        { "station_id": 123 }
        """
        user_id = request['user']['user_id']

        try:
            data = await request.json()
            station_id = data.get('station_id')

            if not station_id:
                self.logger.warning(f"Администратор {user_id}: Не указан station_id для запроса инвентаря.")
                return web.json_response({"error": "Не указан ID станции"}, status=400)

            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                self.logger.warning(f"Администратор {user_id}: Станция с ID {station_id} не найдена.")
                return web.json_response({"error": "Станция не найдена"}, status=404)

            response = await self.query_inventory_handler.send_inventory_request(station_id)

            if response["success"]:
                return web.json_response({
                    "success": True,
                    "message": response["message"],
                    "packet_hex": response.get("packet_hex")
                })
            else:
                return web.json_response({"error": response["message"]}, status=500)

        except Exception as e:
            self.logger.error(f"Администратор {user_id}: Непредвиденная ошибка при запросе инвентаря: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)


    @jwt_middleware
    async def get_station_inventory(self, request: web.Request):
        """
        Возвращает текущий инвентарь станции из кэша соединения.
        GET /api/query-inventory/station/{station_id}
        """
        user_id = request['user']['user_id']
        station_id = request.match_info.get('station_id')

        if not station_id:
            return web.json_response({"error": "Не указан ID станции"}, status=400)

        try:
            station = await Station.get_by_id(self.db_pool, int(station_id))
            if not station:
                return web.json_response({"error": "Станция не найдена"}, status=404)

            # Получаем инвентарь из кэша соединения
            inventory_result = await self.query_inventory_handler.get_station_inventory(int(station_id))
            
            if not inventory_result["success"]:
                return web.json_response({"error": inventory_result["error"]}, status=404)

            inventory_cache = inventory_result["inventory"]
            
            # Формируем ответ, расширяя его полями, ожидаемыми фронтендом
            from models.powerbank import Powerbank
            inventory_data = []
            for slot in inventory_cache.get('inventory', []):
                status_bits = slot.get('status') or {}
                # Преобразуем битовые флаги статуса слота в плоские поля
                error_typec = bool(status_bits.get('TypeCError'))
                error_lightning = bool(status_bits.get('LightningError'))
                error_microusb = bool(status_bits.get('MicroUSBError'))
                powerbank_error = bool(status_bits.get('PowerBankError'))
                has_errors = error_typec or error_lightning or error_microusb or powerbank_error

                # Найдём запись повербанка по серийному (terminal_id)
                powerbank_status = None
                powerbank_id = None
                try:
                    pb = await Powerbank.get_by_serial(self.db_pool, slot['terminal_id'])
                    if pb:
                        powerbank_status = pb.status
                        powerbank_id = pb.powerbank_id
                except Exception:
                    powerbank_status = None

                inventory_data.append({
                    "slot_number": slot['slot_number'],
                    "terminal_id": slot['terminal_id'],
                    # frontend ожидает serial_number
                    "serial_number": slot['terminal_id'],
                    "powerbank_id": powerbank_id,
                    # статус из БД (active, user_reported_broken, system_error, ...)
                    "powerbank_status": powerbank_status,
                    "level": slot['level'],
                    "voltage": slot['voltage'],
                    "current": slot['current'],
                    "temperature": slot['temperature'],
                    "soh": slot['soh'],
                    # оригинальная структура статусов слота
                    "status": status_bits,
                    # плоские флаги ошибок для совместимости с существующим UI
                    "error_typec": error_typec,
                    "error_lightning": error_lightning,
                    "error_microusb": error_microusb,
                    "powerbank_error": powerbank_error,
                    "has_errors": has_errors
                })
            
            # Сортируем по номеру слота
            inventory_data.sort(key=lambda x: x['slot_number'])

            return web.json_response({
                "success": True,
                "station": {
                    "station_id": station.station_id,
                    "box_id": station.box_id,
                    "slots_declared": station.slots_declared,
                    "remain_num": inventory_cache.get('remain_num', station.remain_num),
                    "status": station.status,
                    "last_seen": station.last_seen.isoformat() if station.last_seen else None
                },
                "inventory": inventory_data,
                "cache_info": {
                    "slots_num": inventory_cache.get('slots_num', 0),
                    "last_update": inventory_cache.get('last_update')
                }
            })

        except ValueError:
            return web.json_response({"error": "Неверный формат ID станции"}, status=400)
        except Exception as e:
            self.logger.error(f"Ошибка получения инвентаря станции {station_id} из кэша: {e}", exc_info=True)
            return web.json_response({"error": f"Внутренняя ошибка сервера: {e}"}, status=500)
