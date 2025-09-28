"""
Обработчик для возврата повербанков
"""
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from utils.packet_utils import build_return_power_bank, parse_return_response


class ReturnPowerbankHandler:
    """Обработчик для возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.active_returns = {}  # Словарь активных возвратов: {user_id: {station_id, powerbank_id, timer_task}}
    
    async def start_return_process(self, station_id: int, powerbank_id: int, user_id: int) -> Dict[str, Any]:
        """
        Начинает процесс возврата повербанка с 10-секундным таймером
        """
        try:
            print(f" ReturnPowerbankHandler: Начинаем процесс возврата - station_id={station_id}, powerbank_id={powerbank_id}, user_id={user_id}")
            
            # Проверяем, что станция подключена
            if not self.connection_manager:
                return {"success": False, "message": "Connection manager недоступен"}
            
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"success": False, "message": "Станция не подключена"}
            
            # Проверяем, что повербанк существует и активен
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"success": False, "message": "Повербанк не найден"}
            
            if powerbank.status != 'active':
                return {"success": False, "message": "Повербанк неактивен"}
            
            # Проверяем, что у пользователя есть активный заказ на этот повербанк
            active_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if not active_order or active_order.user_id != user_id:
                return {"success": False, "message": "У вас нет активного заказа на этот повербанк"}
            
            # Отменяем предыдущий процесс возврата для этого пользователя, если есть
            if user_id in self.active_returns:
                await self.cancel_return_process(user_id)
            
            # Создаем задачу таймера
            timer_task = asyncio.create_task(self._return_timer(user_id, station_id, powerbank_id))
            
            # Сохраняем информацию о процессе возврата
            self.active_returns[user_id] = {
                'station_id': station_id,
                'powerbank_id': powerbank_id,
                'timer_task': timer_task,
                'start_time': datetime.now()
            }
            
            print(f" Процесс возврата запущен для пользователя {user_id}, повербанк {powerbank_id}")
            
            return {
                "success": True,
                "message": "Процесс возврата запущен. У вас есть 10 секунд для вставки повербанка.",
                "countdown": 10,
                "powerbank_id": powerbank_id,
                "serial_number": powerbank.serial_number
            }
            
        except Exception as e:
            print(f" Ошибка запуска процесса возврата: {e}")
            return {"success": False, "message": f"Ошибка запуска процесса возврата: {str(e)}"}
    
    async def _return_timer(self, user_id: int, station_id: int, powerbank_id: int):
        """
        Таймер для процесса возврата (10 секунд)
        """
        try:
            await asyncio.sleep(10)  # Ждем 10 секунд
            
            # Проверяем, что процесс все еще активен
            if user_id in self.active_returns:
                print(f" Таймер истек для пользователя {user_id}, отменяем процесс возврата")
                await self.cancel_return_process(user_id, reason="Время истекло")
                
        except asyncio.CancelledError:
            print(f" Таймер возврата отменен для пользователя {user_id}")
        except Exception as e:
            print(f" Ошибка в таймере возврата: {e}")
    
    async def cancel_return_process(self, user_id: int, reason: str = "Отменено пользователем") -> bool:
        """
        Отменяет процесс возврата
        """
        try:
            if user_id in self.active_returns:
                process_info = self.active_returns[user_id]
                timer_task = process_info['timer_task']
                
                # Отменяем задачу таймера
                if not timer_task.done():
                    timer_task.cancel()
                
                # Удаляем из активных процессов
                del self.active_returns[user_id]
                
                print(f" Процесс возврата отменен для пользователя {user_id}: {reason}")
                return True
            
            return False
                    
        except Exception as e:
            print(f" Ошибка отмены процесса возврата: {e}")
            return False
    
    async def process_return(self, station_id: int, powerbank_id: int, user_id: int, 
                           slot_number: int, is_damaged: bool = False, 
                           damage_description: str = None) -> Dict[str, Any]:
        """
        Обрабатывает возврат повербанка
        """
        try:
            print(f" ReturnPowerbankHandler: Обработка возврата - station_id={station_id}, powerbank_id={powerbank_id}, user_id={user_id}, slot={slot_number}")
            
            # Проверяем, что процесс возврата активен
            if user_id not in self.active_returns:
                return {"success": False, "message": "Нет активного процесса возврата"}
            
            process_info = self.active_returns[user_id]
            if process_info['station_id'] != station_id or process_info['powerbank_id'] != powerbank_id:
                return {"success": False, "message": "Неверные параметры возврата"}
            
            # Отменяем таймер
            await self.cancel_return_process(user_id)
            
            # Получаем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"success": False, "message": "Станция не подключена"}
            
            # Создаем команду на возврат повербанка
            secret_key = connection.secret_key
            if not secret_key:
                return {"success": False, "message": "Нет секретного ключа для команды возврата"}
            
            return_command = build_return_power_bank(
                secret_key=secret_key,
                slot=slot_number,
                vsn=1  # Используем VSN=1 по умолчанию
            )
            
            # Отправляем команду через TCP соединение
            if connection.writer and not connection.writer.is_closing():
                connection.writer.write(return_command)
                await connection.writer.drain()
                print(f" Команда на возврат повербанка отправлена станции {station_id}, слот {slot_number}")
                
                # Обновляем статус повербанка если он поврежден
                if is_damaged:
                    await self._mark_powerbank_damaged(powerbank_id, damage_description)
                
                return {
                    "success": True,
                    "message": f"Команда на возврат повербанка отправлена на станцию",
                    "packet_hex": return_command.hex().upper(),
                    "slot_number": slot_number,
                    "is_damaged": is_damaged
                }
            else:
                return {"success": False, "message": "TCP соединение со станцией недоступно"}
                
        except Exception as e:
            print(f" Ошибка обработки возврата: {e}")
            return {"success": False, "message": f"Ошибка обработки возврата: {str(e)}"}
    
    async def _mark_powerbank_damaged(self, powerbank_id: int, damage_description: str = None):
        """
        Помечает повербанк как поврежденный
        """
        try:
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if powerbank:
                # Обновляем статус повербанка
                await powerbank.update_status(self.db_pool, 'user_reported_broken')
                
                # Если есть описание повреждения, можно сохранить его в отдельной таблице
                if damage_description:
                    print(f" Повербанк {powerbank_id} помечен как поврежденный: {damage_description}")
                else:
                    print(f" Повербанк {powerbank_id} помечен как поврежденный")
                    
        except Exception as e:
            print(f" Ошибка пометки повербанка как поврежденного: {e}")
    
    async def handle_return_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ от станции на возврат повербанка
        """
        try:
            # Парсим ответ от станции
            return_response = parse_return_response(data)
            print(f"Обработан ответ на возврат: {return_response}")
            
            station_id = connection.station_id
            if not station_id:
                return
            
            # Проверяем успешность ответа
            if return_response.get('Success', False):
                print("Возврат повербанка успешен")
                
                # Получаем информацию о повербанке из слота
                slot_number = return_response.get('Slot', 0)
                terminal_id = return_response.get('TerminalID', '')
                
                # Находим повербанк по serial_number
                powerbank = await Powerbank.get_by_serial_number(self.db_pool, terminal_id)
                if powerbank:
                    # Создаем заказ на возврат
                    await self._create_return_order(station_id, powerbank.powerbank_id, 1)  # Временный user_id
                    
                    # Добавляем повербанк обратно в станцию
                    await self._add_powerbank_to_station(station_id, powerbank.powerbank_id, slot_number)
                
                # Обновляем last_seen станции
                from models.station import Station
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    # Обновляем remain_num станции (уменьшаем на 1 при возврате)
                    await station.update_remain_num(self.db_pool, int(station.remain_num) - 1)
                
                print(f"Возврат повербанка успешен для станции {station_id}")
                
                # Автоматически запрашиваем инвентарь после успешного возврата
                await self._request_inventory_after_operation(station_id)
            else:
                print(f"Возврат повербанка не удался для станции {station_id}")
                    
        except Exception as e:
             print(f"Ошибка: {e}")
    
    async def _create_return_order(self, station_id: int, powerbank_id: int, user_id: int) -> None:
        """
        Создает запись о возврате повербанка в таблице orders
        """
        try:
            await Order.create_return_order(
                self.db_pool, station_id, user_id, powerbank_id
            )
            print(f"Создан заказ на возврат повербанка {powerbank_id} пользователю {user_id}")
        except Exception as e:
             print(f"Ошибка: {e}")
    
    async def _add_powerbank_to_station(self, station_id: int, powerbank_id: int, slot_number: int) -> None:
        """
        Добавляет повербанк обратно в станцию
        """
        try:
            await StationPowerbank.add_powerbank(
                self.db_pool, station_id, powerbank_id, slot_number
            )
            print(f"Повербанк {powerbank_id} добавлен в слот {slot_number} станции {station_id}")
        except Exception as e:
             print(f"Ошибка: {e}")
    
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
            print(f" Запрос инвентаря отправлен после операции возврата")
            
        except Exception as e:
            print(f" Ошибка запроса инвентаря после операции: {e}")
    
    async def handle_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос на возврат повербанка от станции
        """
        try:
            from utils.packet_utils import parse_return_power_bank_request, build_return_power_bank_response
            
            # Парсим запрос
            request_data = parse_return_power_bank_request(data)
            print(f"Обработан запрос на возврат: {request_data}")
            
            station_id = connection.station_id
            if not station_id:
                print("Не удалось определить station_id из соединения")
                return None
            
            # Создаем ответ
            slot = request_data.get('Slot', 0)
            result = 1  # Успешно
            terminal_id = request_data.get('TerminalID', '').encode('ascii', errors='ignore')
            level = request_data.get('Level', 0)
            voltage = request_data.get('Voltage', 0)
            current = request_data.get('Current', 0)
            temperature = request_data.get('Temperature', 0)
            status = 0  # Нормальный статус
            soh = request_data.get('SOH', 100)
            
            # Создаем ответ
            response = build_return_power_bank_response(
                slot=slot,
                result=result,
                terminal_id=terminal_id,
                level=level,
                voltage=voltage,
                current=current,
                temperature=temperature,
                status=status,
                soh=soh,
                vsn=request_data.get('VSN', 1),
                token=request_data.get('Token', 0)
            )
            
            print(f"Создан ответ на возврат: {response.hex().upper()}")
            return response
            
        except Exception as e:
            print(f"Ошибка: {e}")
            return None

    def get_active_returns(self) -> Dict[int, Dict[str, Any]]:
        """
        Возвращает информацию об активных процессах возврата
        """
        return {
            user_id: {
                'station_id': info['station_id'],
                'powerbank_id': info['powerbank_id'],
                'start_time': info['start_time'].isoformat(),
                'remaining_time': 10 - (datetime.now() - info['start_time']).total_seconds()
            }
            for user_id, info in self.active_returns.items()
        }