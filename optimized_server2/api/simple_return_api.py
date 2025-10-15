"""
Упрощенный API для возврата повербанков
"""
from aiohttp import web
from typing import Dict, Any
from datetime import datetime
from utils.time_utils import get_moscow_time

from models.powerbank import Powerbank
from models.order import Order
from models.station import Station
from models.station_powerbank import StationPowerbank


class SimpleReturnAPI:
    """Упрощенный API для возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def return_powerbank(self, station_id: int, user_id: int, powerbank_id: int) -> Dict[str, Any]:
        """
        Возвращает повербанк (упрощенная версия)
        """
        try:
            print(f" SimpleReturnAPI: Возврат повербанка - station_id={station_id}, user_id={user_id}, powerbank_id={powerbank_id}")
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"error": "Станция не найдена", "success": False}
            
            # Проверяем, что станция активна
            if station.status != 'active':
                return {"error": "Станция неактивна", "success": False}
            
            # Проверяем, что повербанк существует
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"error": "Повербанк не найден", "success": False}
            
            # Проверяем, что у пользователя есть активный заказ на этот повербанк
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if not active_order or active_order.user_id != user_id:
                return {"error": "У вас нет активного заказа на этот повербанк", "success": False}
            
            # Проверяем, что станция подключена
            if not self.connection_manager:
                return {"error": "Connection manager недоступен", "success": False}
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"error": "Станция не подключена", "success": False}
            
            # Создаем команду на возврат повербанка 
            secret_key = connection.secret_key
            if not secret_key:
                return {"error": "Нет секретного ключа для команды возврата", "success": False}
            
            # Используем правильный обработчик возврата
            from handlers.return_powerbank import ReturnPowerbankHandler
            return_handler = ReturnPowerbankHandler(self.db_pool, self.connection_manager)
            
            # Находим свободный слот для возврата
            free_slot = await return_handler._find_free_slot(station_id)
            if not free_slot:
                return {"error": "Нет свободных слотов для возврата", "success": False}
            

            
            # Запускаем процесс возврата
            result = await return_handler.start_return_process(station_id, powerbank_id, user_id)
            
            if result.get('success'):
                return {
                    "success": True,
                    "message": "Процесс возврата запущен. Вставьте повербанк в станцию в течение 10 секунд.",
                    "powerbank_id": powerbank_id,
                    "serial_number": powerbank.serial_number,
                    "station_id": station_id,
                    "timestamp": get_moscow_time().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": result.get('message', 'Ошибка запуска процесса возврата')
                }
                
        except Exception as e:
            print(f" Ошибка возврата повербанка: {e}")
            return {"error": f"Ошибка возврата повербанка: {str(e)}", "success": False}
