"""
API для выдачи повербанков
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

from models.station import Station
from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from handlers.borrow_powerbank import BorrowPowerbankHandler
from utils.station_resolver import StationResolver



class BorrowPowerbankAPI:
    """API для управления выдачей повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.station_resolver = StationResolver(connection_manager) if connection_manager else None
        self.borrow_handler = BorrowPowerbankHandler(db_pool, connection_manager)
    
    async def get_available_powerbanks(self, station_id: int, user_id: int = None) -> Dict[str, Any]:
        """
        Получает список доступных повербанков в станции
        """
        try:
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"error": "Станция не найдена", "success": False}
            
            # Если указан user_id, проверяем права доступа к станции
            if user_id is not None:
                from utils.org_unit_utils import can_user_access_station, log_access_denied_event
                
                can_access_station, station_access_reason = await can_user_access_station(self.db_pool, user_id, station_id)
                if not can_access_station:
                    # Логируем отказ в доступе к станции
                    await log_access_denied_event(self.db_pool, user_id, 'station', station_id, station_access_reason)
                    
                    return {"error": station_access_reason, "success": False}
            
            # Получаем повербанки в станции
            powerbanks = await StationPowerbank.get_station_powerbanks(self.db_pool, station_id)
            
            result = []
            for sp in powerbanks:
                powerbank = await Powerbank.get_by_id(self.db_pool, sp.powerbank_id)
                if powerbank and powerbank.status == 'active':
                    # Проверяем, что повербанк не находится в активном заказе
                    existing_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                    if existing_order:
                        continue  # Пропускаем повербанки в активных заказах
                    
                    # Проверяем наличие ошибок в статусе
                    has_errors = self._check_powerbank_errors(sp)
                    
                    result.append({
                        "slot_number": sp.slot_number,
                        "powerbank_id": sp.powerbank_id,
                        "serial_number": powerbank.serial_number,
                        "level": sp.level,
                        "voltage": sp.voltage,
                        "temperature": sp.temperature,
                        "soh": powerbank.soh,
                        "has_errors": has_errors,
                        "last_update": sp.last_update.isoformat() if sp.last_update else None
                    })
            
            return {
                "success": True,
                "station_id": station_id,
                "available_powerbanks": result,
                "count": len(result)
            }
            
        except Exception as e:
            return {"error": f"Ошибка получения повербанков: {str(e)}", "success": False}
    
    async def request_borrow(self, station_id: int, slot_number: int, user_id: int) -> Dict[str, Any]:
        """
        Запрашивает выдачу повербанка из указанного слота
        """
        try:
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"error": "Станция не найдена", "success": False}
            
            # Проверяем, что станция активна
            if station.status != 'active':
                return {"error": "Станция неактивна", "success": False}
            
            # Проверяем онлайн статус станции
            from models.connection import ConnectionManager
            connection_manager = self.connection_manager
            if connection_manager:
                connection = connection_manager.get_connection_by_station_id(station_id)
                if not connection:
                    return {"error": "Станция не подключена", "success": False}
                
                # Проверяем последний heartbeat (не более 30 секунд назад)
                if connection.last_heartbeat:
                    from datetime import datetime
                    from utils.time_utils import get_moscow_time
                    time_since_heartbeat = (get_moscow_time() - connection.last_heartbeat).total_seconds()
                    if time_since_heartbeat > 30:
                        return {"error": f"Станция офлайн (последний heartbeat {time_since_heartbeat:.0f} секунд назад)", "success": False}
                else:
                    return {"error": "Станция не отправляла heartbeat", "success": False}
            
            # Проверяем права доступа пользователя к станции
            from utils.org_unit_utils import can_user_access_station, log_access_denied_event
            
            can_access_station, station_access_reason = await can_user_access_station(self.db_pool, user_id, station_id)
            if not can_access_station:
                # Логируем отказ в доступе к станции
                await log_access_denied_event(self.db_pool, user_id, 'station', station_id, station_access_reason)
                
                return {"error": station_access_reason, "success": False}
            
            # Проверяем, есть ли повербанк в слоте
            station_powerbank = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, slot_number
            )
            
            if not station_powerbank:
                return {"error": f"В слоте {slot_number} нет повербанка", "success": False}
            
            # Комплексная валидация запроса на выдачу с защитой от дублирования
            from utils.order_utils import validate_borrow_request
            request_valid, validation_message = await validate_borrow_request(
                self.db_pool, user_id, station_powerbank.powerbank_id, station_id
            )
            
            if not request_valid:
                return {"error": validation_message, "success": False}
            
            # Получаем информацию о powerbank'е (уже проверенном в validate_borrow_request)
            powerbank = await Powerbank.get_by_id(self.db_pool, station_powerbank.powerbank_id)
            
            # Проверяем, что станция была онлайн в течение последних 30 секунд
            from utils.station_utils import validate_station_for_operation
            station_valid, station_message = await validate_station_for_operation(
                self.db_pool, self.connection_manager, station_id, "выдача powerbank'а", 30
            )
            
            if not station_valid:
                return {"error": station_message, "success": False}
            
            # Запрашиваем актуальный инвентарь станции для синхронизации данных
            await self._request_inventory_before_operation(station_id)
            import asyncio
            await asyncio.sleep(2)  # Даем время на обновление данных
            
            # Повторно проверяем наличие повербанка в слоте после синхронизации
            station_powerbank_updated = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, slot_number
            )
            
            if not station_powerbank_updated:
                return {"error": "Повербанк больше не находится в слоте после синхронизации", "success": False}
            
            # Проверяем, что это тот же повербанк
            if station_powerbank_updated.powerbank_id != station_powerbank.powerbank_id:
                return {"error": "В слоте находится другой повербанк", "success": False}
            
            # Получаем соединение (уже проверенное в validate_station_for_operation)
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            
            # Создаем заказ на выдачу
            order = await Order.create_borrow_order(
                self.db_pool, station_id, user_id, powerbank.powerbank_id
            )
            
            if not order:
                return {"error": "Не удалось создать заказ", "success": False}
            
            # Отправляем команду на выдачу станции и ждем ответа
            borrow_result = await self.borrow_handler.send_borrow_request_and_wait(
                station_id, 
                powerbank.powerbank_id, 
                user_id,
                order.order_id
            )
            
            if not borrow_result["success"]:
                # Если команда не отправилась или станция отклонила, отменяем заказ
                await Order.cancel(self.db_pool, order.order_id)
                return {
                    "success": False,
                    "error": f"Ошибка выдачи повербанка: {borrow_result['message']}"
                }
            
            # Подтверждаем заказ после успешной выдачи
            await Order.confirm_borrow(self.db_pool, order.order_id)
            
            # Запрашиваем инвентарь для проверки, что повербанк действительно выдался
            await self._request_inventory_after_operation(station_id)
            
            return {
                "success": True,
                "message": f"Повербанк {powerbank.serial_number} успешно выдан из слота {slot_number}",
                "order_id": order.order_id,
                "station_id": station_id,
                "slot_number": slot_number,
                "powerbank_id": powerbank.powerbank_id,
                "serial_number": powerbank.serial_number,
                "user_id": user_id
            }
            
        except Exception as e:
            return {"error": f"Ошибка запроса выдачи: {str(e)}", "success": False}
    
    async def get_borrow_status(self, station_id: int, slot_number: int) -> Dict[str, Any]:
        """
        Получает статус выдачи повербанка
        """
        try:
            # Проверяем, есть ли повербанк в слоте
            station_powerbank = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, slot_number
            )
            
            if not station_powerbank:
                return {
                    "success": True,
                    "slot_number": slot_number,
                    "status": "empty",
                    "message": "Слот пуст"
                }
            
            powerbank = await Powerbank.get_by_id(self.db_pool, station_powerbank.powerbank_id)
            
            return {
                "success": True,
                "slot_number": slot_number,
                "status": "occupied",
                "powerbank_id": station_powerbank.powerbank_id,
                "serial_number": powerbank.serial_number if powerbank else "unknown",
                "powerbank_status": powerbank.status if powerbank else "unknown",
                "level": station_powerbank.level,
                "voltage": station_powerbank.voltage,
                "temperature": station_powerbank.temperature
            }
            
        except Exception as e:
            return {"error": f"Ошибка получения статуса: {str(e)}", "success": False}
    
    async def get_station_info(self, station_id: int) -> Dict[str, Any]:
        """
        Получает информацию о станции и доступных повербанках
        """
        try:
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"error": "Станция не найдена", "success": False}
            
            # Получаем информацию о подключении 
            is_connected = False
            if self.connection_manager:
                connection = self.connection_manager.get_connection_by_station_id(station_id)
                is_connected = connection is not None
            
            # Получаем повербанки
            powerbanks = await StationPowerbank.get_station_powerbanks(self.db_pool, station_id)
            active_powerbanks = [sp for sp in powerbanks if sp.powerbank_id]
            
            return {
                "success": True,
                "station": {
                    "station_id": station.station_id,
                    "box_id": station.box_id,
                    "org_unit_id": station.org_unit_id,
                    "slots_declared": station.slots_declared,
                    "remain_num": station.remain_num,
                    "status": station.status,
                    "last_seen": station.last_seen.isoformat() if station.last_seen else None,
                    "is_connected": is_connected
                },
                "powerbanks": {
                    "total_slots": station.slots_declared,
                    "occupied_slots": len(active_powerbanks),
                    "available_slots": int(station.slots_declared) - len(active_powerbanks)
                }
            }
            
        except Exception as e:
            return {"error": f"Ошибка получения информации о станции: {str(e)}", "success": False}
    
    def _check_powerbank_errors(self, station_powerbank) -> bool:
        """
        Проверяет наличие ошибок у повербанка
        Возвращает True если есть ошибки
        """
        # Проверяем критические параметры
        if station_powerbank.level is not None and station_powerbank.level < 5:
            return True  # Критически низкий заряд
        
        if station_powerbank.voltage is not None:
            if station_powerbank.voltage < 3000 or station_powerbank.voltage > 4500:
                return True  # Некорректное напряжение
        
        if station_powerbank.temperature is not None:
            if station_powerbank.temperature < -10 or station_powerbank.temperature > 60:
                return True  # Критическая температура
        
        return False
    
    async def select_optimal_powerbank(self, station_id: int) -> Dict[str, Any]:
        """
        Выбирает оптимальный повербанк для выдачи по правилам:
        1. Максимальный уровень заряда
        2. Без ошибок
        3. Статус активный
        4. Если все нормальные - случайный выбор
        """
        try:
            # Получаем все активные повербанки в станции
            powerbanks = await StationPowerbank.get_station_powerbanks(self.db_pool, station_id)
            
            if not powerbanks:
                return {"error": "В станции нет повербанков", "success": False}
            
            # Проверяем статус станции
            station = await Station.get_by_id(self.db_pool, station_id)
            if station and station.status != 'active':
                return {"error": f"Станция неактивна (статус: {station.status})", "success": False}
            
            # Фильтруем только активные повербанки, не находящиеся в заказах
            active_powerbanks = []
            for sp in powerbanks:
                powerbank = await Powerbank.get_by_id(self.db_pool, sp.powerbank_id)
                if powerbank and powerbank.status == 'active':
                    # Проверяем, что повербанк не находится в активном заказе
                    existing_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank.powerbank_id)
                    if existing_order:
                        print(f" Повербанк {powerbank.serial_number} уже в заказе, пропускаем")
                        continue
                    
                    has_errors = self._check_powerbank_errors(sp)
                    active_powerbanks.append({
                        'station_powerbank': sp,
                        'powerbank': powerbank,
                        'has_errors': has_errors,
                        'level': sp.level or 0
                    })
            
            if not active_powerbanks:
                return {"error": "Нет активных повербанков в станции", "success": False}
            
            # Разделяем на группы: без ошибок и с ошибками
            healthy_powerbanks = [pb for pb in active_powerbanks if not pb['has_errors']]
            error_powerbanks = [pb for pb in active_powerbanks if pb['has_errors']]
            
            selected_powerbank = None
            selection_reason = ""
            
            if healthy_powerbanks:
                # Если есть здоровые повербанки, выбираем с максимальным зарядом
                if len(healthy_powerbanks) == 1:
                    selected_powerbank = healthy_powerbanks[0]
                    selection_reason = "Единственный здоровый повербанк"
                else:
                    # Сортируем по уровню заряда (по убыванию)
                    healthy_powerbanks.sort(key=lambda x: x['level'], reverse=True)
                    
                    # Если все имеют одинаковый максимальный заряд - случайный выбор
                    max_level = healthy_powerbanks[0]['level']
                    max_level_powerbanks = [pb for pb in healthy_powerbanks if pb['level'] == max_level]
                    
                    if len(max_level_powerbanks) == 1:
                        selected_powerbank = max_level_powerbanks[0]
                        selection_reason = f"Максимальный заряд: {max_level}%"
                    else:
                        # Случайный выбор среди повербанков с максимальным зарядом
                        import random
                        selected_powerbank = random.choice(max_level_powerbanks)
                        selection_reason = f"Случайный выбор среди повербанков с зарядом {max_level}%"
            else:
                # Если все повербанки с ошибками, выбираем случайный
                import random
                selected_powerbank = random.choice(active_powerbanks)
                selection_reason = "Случайный выбор (все повербанки имеют ошибки)"
            
            if not selected_powerbank:
                return {"error": "Не удалось выбрать повербанк", "success": False}
            
            sp = selected_powerbank['station_powerbank']
            powerbank = selected_powerbank['powerbank']
            
            return {
                "success": True,
                "selected_powerbank": {
                    "slot_number": sp.slot_number,
                    "powerbank_id": sp.powerbank_id,
                    "serial_number": powerbank.serial_number,
                    "level": sp.level,
                    "voltage": sp.voltage,
                    "temperature": sp.temperature,
                    "soh": powerbank.soh,
                    "has_errors": selected_powerbank['has_errors']
                },
                "selection_reason": selection_reason,
                "total_available": len(active_powerbanks),
                "healthy_count": len(healthy_powerbanks),
                "error_count": len(error_powerbanks)
            }
            
        except Exception as e:
            return {"error": f"Ошибка выбора повербанка: {str(e)}", "success": False}
    
    async def _request_inventory_before_operation(self, station_id: int) -> None:
        """
        Запрашивает актуальный инвентарь станции перед операцией
        """
        try:
            from handlers.query_inventory import QueryInventoryHandler
            inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
            await inventory_handler.send_inventory_request(station_id)
            
            from utils.centralized_logger import get_logger
            logger = get_logger('borrow_powerbank_api')
            logger.info(f"Запрос инвентаря отправлен перед операцией выдачи на станцию {station_id}")
            
        except Exception as e:
            from utils.centralized_logger import get_logger
            logger = get_logger('borrow_powerbank_api')
            logger.error(f"Ошибка запроса инвентаря перед операцией: {e}")
    
    async def _request_inventory_after_operation(self, station_id: int) -> None:
        """
        Запрашивает инвентарь после операции с повербанком
        """
        try:
            from utils.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(self.db_pool)
            
            # Получаем соединение со станцией
            connection = self.borrow_handler.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                print(f"Соединение со станцией {station_id} не найдено")
                return
            
            await inventory_manager.request_inventory_after_operation(station_id, connection)
            print(f"Запрос инвентаря отправлен после операции выдачи")
            
        except Exception as e:
            print(f"Ошибка запроса инвентаря после операции: {e}")
    
    async def request_optimal_borrow(self, station_id: int, user_id: int) -> Dict[str, Any]:
        """
        Запрашивает выдачу оптимального повербанка (автоматический выбор)
        """
        try:
            # Проверяем права доступа пользователя к станции
            from utils.org_unit_utils import can_user_access_station, log_access_denied_event
            
            can_access_station, station_access_reason = await can_user_access_station(self.db_pool, user_id, station_id)
            if not can_access_station:
                # Логируем отказ в доступе к станции
                await log_access_denied_event(self.db_pool, user_id, 'station', station_id, station_access_reason)
                
                return {"error": station_access_reason, "success": False}
            
            # Выбираем оптимальный повербанк
            selection_result = await self.select_optimal_powerbank(station_id)
            
            if not selection_result.get('success'):
                return selection_result
            
            selected = selection_result['selected_powerbank']
            slot_number = selected['slot_number']
            powerbank_id = selected['powerbank_id']
            
            # Запрашиваем актуальный инвентарь станции для синхронизации данных
            await self._request_inventory_before_operation(station_id)
            import asyncio
            await asyncio.sleep(2)  # Даем время на обновление данных
            
            # Повторно проверяем наличие повербанка в слоте после синхронизации
            station_powerbank_updated = await StationPowerbank.get_by_slot(
                self.db_pool, station_id, slot_number
            )
            
            if not station_powerbank_updated:
                return {"error": "Повербанк больше не находится в слоте после синхронизации", "success": False}
            
            # Проверяем, что это тот же повербанк
            if station_powerbank_updated.powerbank_id != powerbank_id:
                return {"error": "В слоте находится другой повербанк", "success": False}
            
            # Проверяем, что повербанк не находится в активном заказе
            existing_order = await Order.get_active_by_powerbank_id(self.db_pool, powerbank_id)
            if existing_order:
                return {
                    "success": False,
                    "error": f"Повербанк {selected['serial_number']} уже находится в активном заказе"
                }
            
            # Проверяем, что пользователь существует
            from models.user import User
            user = await User.get_by_id(self.db_pool, int(user_id))
            if not user:
                return {
                    "success": False,
                    "error": f"Пользователь с ID {user_id} не найден"
                }
            
            # Создаем заказ на выдачу
            order = await Order.create_borrow_order(
                self.db_pool, station_id, int(user_id), selected['powerbank_id']
            )
            
            if not order:
                return {
                    "success": False,
                    "error": "Не удалось создать заказ"
                }
            
            # Отправляем команду выдачи на станцию и ждем ответа
            borrow_result = await self.borrow_handler.send_borrow_request_and_wait(
                station_id, 
                selected['powerbank_id'], 
                int(user_id),
                order.order_id
            )
            
            if not borrow_result["success"]:
                # Если команда не отправилась или станция отклонила, отменяем заказ
                await Order.cancel(self.db_pool, order.order_id)
                return {
                    "success": False,
                    "error": f"Ошибка выдачи повербанка: {borrow_result['message']}"
                }
            
            # Подтверждаем заказ после успешной выдачи
            await Order.confirm_borrow(self.db_pool, order.order_id)
            
            # Запрашиваем инвентарь для проверки, что повербанк действительно выдался
            await self._request_inventory_after_operation(station_id)
            
            return {
                "success": True,
                "message": f"Повербанк {selected['serial_number']} успешно выдан из слота {slot_number}",
                "order_id": order.order_id,
                "station_id": station_id,
                "slot_number": slot_number,
                "powerbank_id": selected['powerbank_id'],
                "serial_number": selected['serial_number'],
                "user_id": user_id,
                "selection_info": {
                    "reason": selection_result['selection_reason'],
                    "total_available": selection_result['total_available'],
                    "healthy_count": selection_result['healthy_count'],
                    "error_count": selection_result['error_count']
                }
            }
            
        except Exception as e:
            return {"error": f"Ошибка запроса оптимальной выдачи: {str(e)}", "success": False}
    
    async def request_borrow_by_powerbank_id(self, powerbank_id: int, user_id: int) -> Dict[str, Any]:
        """
        Запрашивает выдачу повербанка по его ID (автоматически определяет станцию)
        """
        try:
            if not self.station_resolver:
                return {"error": "Station resolver недоступен", "success": False}
            
            # Определяем станцию по ID повербанка
            station_info = self.station_resolver.resolve_station_by_powerbank_id(powerbank_id, self.db_pool)
            if not station_info:
                return {"error": "Повербанк не найден в станции", "success": False}
            
            if not station_info["is_connected"]:
                return {"error": "Станция не подключена", "success": False}
            
            station_id = station_info["station_id"]
            slot_number = station_info["slot_number"]
            
            # Используем существующий метод (в нем уже есть проверка доступа)
            return await self.request_borrow(station_id, slot_number, user_id)
            
        except Exception as e:
            return {"error": f"Ошибка запроса выдачи по ID повербанка: {str(e)}", "success": False}
