"""
Упрощенный API для возврата повербанков
"""
from aiohttp import web
from typing import Dict, Any
from datetime import datetime

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
            
            # Создаем команду на возврат повербанка (используем слот 1 по умолчанию)
            secret_key = connection.secret_key
            if not secret_key:
                return {"error": "Нет секретного ключа для команды возврата", "success": False}
            
            from utils.packet_utils import build_return_power_bank
            return_command = build_return_power_bank(
                secret_key=secret_key,
                slot=1,  # Используем слот 1 по умолчанию
                vsn=1
            )
            
            # Отправляем команду через TCP соединение
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(return_command)
                await connection.writer.drain()
                print(f" Команда на возврат повербанка отправлена станции {station_id}")
                
                # Создаем заказ на возврат
                await Order.create_return_order(
                    self.db_pool, station_id, user_id, powerbank_id
                )
                
                # Обновляем статус заказа на возврат
                await active_order.update_status(self.db_pool, 'return')
                
                return {
                    "success": True,
                    "message": "Повербанк возвращен успешно",
                    "powerbank_id": powerbank_id,
                    "serial_number": powerbank.serial_number,
                    "station_id": station_id,
                    "packet_hex": return_command.hex().upper(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": "TCP соединение со станцией недоступно", "success": False}
                
        except Exception as e:
            print(f" Ошибка возврата повербанка: {e}")
            return {"error": f"Ошибка возврата повербанка: {str(e)}", "success": False}
