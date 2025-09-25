"""
Обработчик для выдачи повербанков
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from utils.packet_utils import build_borrow_power_bank, parse_borrow_request, parse_borrow_response


class BorrowPowerbankHandler:
    """Обработчик для выдачи повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_borrow_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на выдачу повербанка
        Возвращает команду для отправки на станцию или None
        """
        try:
            # Парсим запрос на выдачу
            borrow_request = parse_borrow_request(data)
            print(f"Обработан запрос на выдачу: слот {borrow_request['Slot']}")
            
            # Получаем информацию о станции
            station_id = connection.station_id
            if not station_id:
                print("Станция не найдена для соединения")
                return None
            
            requested_slot = borrow_request['Slot']
            
            # Проверяем, есть ли повербанк в запрашиваемом слоте
            station_powerbank = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, requested_slot
            )
            
            if not station_powerbank:
                print(f"В слоте {requested_slot} станции {station_id} нет повербанка")
                return None
            
            # Проверяем, что повербанк активен
            powerbank = await Powerbank.get_by_id(self.db_pool, station_powerbank.powerbank_id)
            if not powerbank or powerbank.status != 'active':
                print(f"Повербанк в слоте {requested_slot} не активен")
                return None
            
            # Проверяем, что повербанк не выдан повторно (защита от дублирования)
            if await self._is_powerbank_already_borrowed(powerbank.powerbank_id):
                print(f"Повербанк {powerbank.serial_number} уже выдан и не может быть выдан повторно")
                return None
            
            # Дополнительная проверка: убеждаемся, что повербанк все еще в станции
            if not await self._is_powerbank_in_station(station_id, powerbank.powerbank_id):
                print(f"Повербанк {powerbank.serial_number} больше не находится в станции")
                return None
            
            # Получаем секретный ключ
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для команды выдачи")
                return None
            
            # Создаем команду на выдачу повербанка
            borrow_command = build_borrow_power_bank(
                secret_key=secret_key,
                slot=requested_slot,
                vsn=borrow_request['VSN']
            )
            
            print(f"Создана команда на выдачу повербанка из слота {requested_slot}")
            return borrow_command
            
        except Exception as e:
            print(f"Ошибка обработки запроса на выдачу: {e}")
            return None
    
    async def handle_borrow_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ от станции на выдачу повербанка
        """
        try:
            # Парсим ответ от станции
            borrow_response = parse_borrow_response(data)
            print(f"Обработан ответ на выдачу: {borrow_response}")
            
            station_id = connection.station_id
            if not station_id:
                return
            
            # Проверяем успешность ответа
            if borrow_response.get('Success', False):
                print("Выдача повербанка успешна")
                
                # Получаем информацию о повербанке из слота
                slot_number = borrow_response.get('Slot', 0)
                station_powerbank = await StationPowerbank.get_by_slot(
                    self.db_pool, station_id, slot_number
                )
                
                if station_powerbank:
                    # Создаем заказ на выдачу повербанка
                    await self._create_borrow_order(
                        station_id, 
                        station_powerbank.powerbank_id, 
                        user_id=1  # Временный user_id, в реальной системе должен быть из сессии
                    )
                    
                    # Удаляем повербанк из станции
                    await self.process_successful_borrow(station_id, slot_number)
                
                # Обновляем last_seen станции
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    # Обновляем remain_num станции (увеличиваем на 1 при выдаче)
                    await station.update_remain_num(self.db_pool, int(station.remain_num) + 1)
                
                print(f"Выдача повербанка успешна для станции {station_id}")
                
                # Автоматически запрашиваем инвентарь после успешной выдачи
                await self._request_inventory_after_operation(station_id)
            else:
                print(f"Выдача повербанка не удалась для станции {station_id}")
            
        except Exception as e:
            print(f"Ошибка обработки ответа на выдачу: {e}")
    
    async def process_successful_borrow(self, station_id: int, slot_number: int) -> None:
        """
        Обрабатывает успешную выдачу повербанка
        Удаляет повербанк из station_powerbank
        """
        try:
            success = await StationPowerbank.remove_powerbank(
                self.db_pool, station_id, slot_number
            )
            
            if success:
                print(f"Повербанк успешно удален из слота {slot_number} станции {station_id}")
            else:
                print(f"Не удалось удалить повербанк из слота {slot_number}")
                
        except Exception as e:
            print(f"Ошибка при удалении повербанка из станции: {e}")
    
    async def _create_borrow_order(self, station_id: int, powerbank_id: int, user_id: int) -> None:
        """
        Создает запись о выдаче повербанка в таблице orders
        """
        try:
            await Order.create_borrow_order(
                self.db_pool, station_id, user_id, powerbank_id
            )
            print(f"Создан заказ на выдачу повербанка {powerbank_id} пользователю {user_id}")
        except Exception as e:
            print(f"Ошибка создания заказа: {e}")
    
    async def get_available_slots(self, station_id: int) -> list:
        """
        Получает список доступных слотов для выдачи
        """
        try:
            slots = await StationPowerbank.get_station_slots(self.db_pool, station_id)
            return slots
        except Exception as e:
            print(f"Ошибка получения слотов: {e}")
            return []
    
    async def _is_powerbank_already_borrowed(self, powerbank_id: int) -> bool:
        """
        Проверяет, не выдан ли уже повербанк (защита от повторной выдачи)
        """
        try:
            # Проверяем, есть ли активный заказ на выдачу этого повербанка
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT COUNT(*) as count 
                        FROM orders 
                        WHERE powerbank_id = %s 
                        AND status = 'borrow' 
                        AND timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    """, (powerbank_id,))
                    
                    result = await cur.fetchone()
                    return result[0] > 0
                    
        except Exception as e:
            print(f"Ошибка проверки статуса повербанка {powerbank_id}: {e}")
            return False
    
    async def _is_powerbank_in_station(self, station_id: int, powerbank_id: int) -> bool:
        """
        Проверяет, что повербанк все еще находится в станции
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT COUNT(*) as count 
                        FROM station_powerbank 
                        WHERE station_id = %s AND powerbank_id = %s
                    """, (station_id, powerbank_id))
                    
                    result = await cur.fetchone()
                    return result[0] > 0
                    
        except Exception as e:
            print(f"Ошибка проверки наличия повербанка в станции: {e}")
            return False
    
    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции с повербанком
        """
        try:
            from utils.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(self.db_pool)
            
            # Получаем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                print(f"Соединение со станцией {station_id} не найдено")
                return
            
            await inventory_manager.request_inventory_after_operation(station_id, connection)
            print(f"📦 Запрос инвентаря отправлен после операции выдачи")
            
        except Exception as e:
            print(f"❌ Ошибка запроса инвентаря после операции: {e}")
