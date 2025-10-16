from typing import Optional, Dict, Any
import struct
import asyncio
from datetime import datetime

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from models.station import Station
from models.slot_abnormal_report import SlotAbnormalReport
from models.powerbank_error import PowerbankError
from utils.centralized_logger import get_logger
from utils.packet_utils import (
    parse_return_power_bank_request,
    build_return_power_bank_response,
    generate_session_token
)


class ReturnPowerbankHandler:
    """Обработчик возврата повербанков"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('return_powerbank')
        # Словарь для отслеживания ожидающих возвратов с ошибкой
        self.pending_error_returns = {}
    
    async def handle_return_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос от станции на возврат повербанка (0x66)
        
        Протокол 3.5.1 Cabinet → Server:
        - Станция отправляет: Slot, TerminalID, Level, Voltage, Current, Temperature, Status, SOH
        
        Логика:
        1. Проверяем повербанк в БД по TerminalID
           - Если НЕТ → создаем со статусом 'unknown'
        2. Проверяем слот
           - Если занят → Result=5 (Slot not empty)
        3. Проверяем активный заказ (status='borrow')
           - Если есть → меняем на status='return'
        4. Добавляем повербанк в station_powerbank
        5. Обновляем remain_num станции
        6. Отвечаем Result=1 (Success)
        
        Протокол 3.5.2 Server → Cabinet:
        - Сервер отвечает: Slot, Result (0-5), TerminalID, Level, Voltage, Current, Temperature, Status, SOH
        """
        try:
            # Парсим запрос от станции
            request = parse_return_power_bank_request(data)
            
            if 'error' in request:
                self.logger.error(f"Ошибка парсинга запроса возврата: {request.get('error')}")
                return None
            
            station_id = connection.station_id
            if not station_id:
                self.logger.warning("Запрос возврата от неавторизованной станции")
                return None
            
            # Извлекаем данные из запроса
            slot = request.get('Slot', 0)
            terminal_id = request.get('TerminalID', '')
            level = request.get('Level', 0)
            voltage = request.get('Voltage', 0)
            current = request.get('Current', 0)
            temperature = request.get('Temperature', 0)
            status = request.get('Status', 0)
            soh = request.get('SOH', 100)
            vsn = request.get('VSN', 1)
            
            self.logger.info(f"📥 Возврат: станция {station_id}, слот {slot}, TerminalID={terminal_id}")
            
            # Проверяем, есть ли ожидающий возврат с ошибкой для этой станции
            pending_key = None
            for key, pending_data in self.pending_error_returns.items():
                if pending_data['station_id'] == station_id:
                    pending_key = key
                    break
            
            if pending_key:
                # Это возврат с ошибкой - обрабатываем специально
                await self.handle_error_return_response(data, connection)
                # Отвечаем станции успешно
                return self._build_response(
                    connection.secret_key, slot, 1,
                    terminal_id.encode('utf-8')[:8].ljust(8, b'\x00'),
                    level, voltage, current, temperature, status, soh, vsn
                )
            
            # Проверка 1: TerminalID должен быть
            if not terminal_id:
                self.logger.error(f"Отсутствует TerminalID от станции {station_id}")
                return self._build_response(
                    connection.secret_key, slot, 4, b'\x00' * 8,
                    0, 0, 0, 0, 0, 0, vsn
                )
            
            # Проверка 2: Повербанк в БД
            try:
                powerbank = await Powerbank.get_by_serial(self.db_pool, terminal_id)
            except Exception as e:
                self.logger.error(f"Ошибка получения повербанка {terminal_id}: {e}")
                powerbank = None
            
            # Если повербанка нет в БД → создаем со статусом 'unknown'
            if not powerbank:
                self.logger.warning(f"⚠️ Повербанк {terminal_id} НЕ НАЙДЕН в БД → создаем со статусом 'unknown'")
                try:
                    # Получаем org_unit_id станции (если есть)
                    station = await Station.get_by_id(self.db_pool, station_id)
                    org_unit_id = station.org_unit_id if station else None
                    
                    # Создаем повербанк со статусом 'unknown'
                    powerbank = await Powerbank.create_unknown(
                        self.db_pool, terminal_id, org_unit_id
                    )
                    self.logger.info(
                        f"✅ Повербанк {terminal_id} создан: "
                        f"powerbank_id={powerbank.powerbank_id}, status='unknown'"
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка создания повербанка {terminal_id}: {e}")
                    # Если не удалось создать, возвращаем ошибку
                    return self._build_response(
                        connection.secret_key, slot, 4,
                        terminal_id.encode('utf-8')[:8].ljust(8, b'\x00'),
                        level, voltage, current, temperature, status, soh, vsn
                    )
            else:
                self.logger.info(f"✅ Повербанк найден: powerbank_id={powerbank.powerbank_id}, status='{powerbank.status}'")
            
            # Проверка 3: Слот не должен быть занят
            existing_in_slot = await StationPowerbank.get_by_station_and_slot(
                self.db_pool, station_id, slot
            )
            
            if existing_in_slot:
                self.logger.warning(f"⚠️ Слот {slot} уже занят повербанком {existing_in_slot.powerbank_id}")
                # Result=5: Slot not empty
                return self._build_response(
                    connection.secret_key, slot, 5,
                    terminal_id.encode('utf-8')[:8].ljust(8, b'\x00'),
                    level, voltage, current, temperature, status, soh, vsn
                )
            
            # Проверка 4: Есть ли активный заказ со статусом 'borrow'
            active_order = None
            try:
                active_order = await Order.get_active_borrow_order(
                    self.db_pool, powerbank.powerbank_id
                )
            except Exception as e:
                self.logger.error(f"Ошибка проверки активного заказа: {e}")
            
            # Если есть активный заказ → закрываем (borrow → return)
            if active_order:
                try:
                    await Order.update_order_status(
                        self.db_pool, active_order.order_id, 'return'
                    )
                    self.logger.info(
                        f"✅ Заказ {active_order.order_id} закрыт: "
                        f"borrow → return (повербанк {terminal_id})"
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка закрытия заказа {active_order.order_id}: {e}")
            else:
                self.logger.info(f"ℹ️ Активный заказ для повербанка {terminal_id} не найден")
            
            # Добавляем повербанк в station_powerbank
            try:
                await StationPowerbank.add_powerbank(
                    self.db_pool,
                    station_id,
                    powerbank.powerbank_id,
                    slot,
                    level=level,
                    voltage=voltage,
                    temperature=temperature
                )
                self.logger.info(
                    f"✅ Повербанк {terminal_id} добавлен в station_powerbank "
                    f"(станция {station_id}, слот {slot})"
                )
            except Exception as e:
                self.logger.error(f"Ошибка добавления в station_powerbank: {e}")
                # Всё равно отвечаем Success, повербанк принят
            
            # Обновляем данные станции
            try:
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    new_remain = int(station.remain_num) + 1
                    await station.update_remain_num(self.db_pool, new_remain)
                    self.logger.info(f"✅ Станция {station_id}: remain_num {station.remain_num} → {new_remain}")
            except Exception as e:
                self.logger.error(f"Ошибка обновления станции: {e}")
            
            # Запрашиваем инвентарь для синхронизации
            try:
                from handlers.query_inventory import QueryInventoryHandler
                inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
                await inventory_handler.send_inventory_request(station_id)
                self.logger.info(f"📊 Запрос инвентаря отправлен на станцию {station_id}")
            except Exception as e:
                self.logger.error(f"Ошибка запроса инвентаря: {e}")
            
            # Формируем успешный ответ: Result=1 (Success)
            response = self._build_response(
                connection.secret_key, slot, 1,
                terminal_id.encode('utf-8')[:8].ljust(8, b'\x00'),
                level, voltage, current, temperature, status, soh, vsn
            )
            
            self.logger.info(f"✅ Возврат повербанка {terminal_id} успешно обработан")
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки возврата: {e}", exc_info=True)
            return None
    
    def _build_response(self, secret_key: str, slot: int, result: int,
                       terminal_id: bytes, level: int, voltage: int,
                       current: int, temperature: int, status: int,
                       soh: int, vsn: int) -> bytes:
        """
        Строит ответ сервера на возврат повербанка (3.5.2)
        
        Args:
            secret_key: Секретный ключ станции
            slot: Номер слота
            result: Результат (0: Failure, 1: Success, 2: Status Error, 
                              3: Duplicate, 4: Invalid ID, 5: Slot not empty)
            terminal_id: ID повербанка (8 байт)
            level: Уровень заряда (0-100)
            voltage: Напряжение (mV)
            current: Ток (mA)
            temperature: Температура (-127 to 128)
            status: Статус bitmap
            soh: Здоровье батареи (0-100)
            vsn: Версия протокола
            
        Returns:
            bytes: Пакет ответа
        """
        # Формируем payload для вычисления токена
        payload = struct.pack(
            ">BB8sBHHbBB",
            slot, result, terminal_id, level, voltage, current, 
            temperature, status, soh
        )
        
        # Генерируем токен
        token = generate_session_token(payload, secret_key)
        
        # Строим ответ
        response = build_return_power_bank_response(
            slot, result, terminal_id, level, voltage, current,
            temperature, status, soh, vsn, token
        )
        
        return response
    
    async def start_damage_return_process(self, station_id: int, user_id: int, description: str, error_type: str = 'other') -> Dict[str, Any]:
        """
        Инициирует процесс возврата повербанка с поломкой
        
        Args:
            station_id: ID станции
            user_id: ID пользователя
            description: Описание проблемы
            error_type: Тип ошибки (broken, lost, other)
            
        Returns:
            Dict с результатом операции
        """
        try:
            self.logger.info(f"Инициация возврата с поломкой: станция {station_id}, пользователь {user_id}, описание: {description}, тип ошибки: {error_type}")
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "message": "Станция не найдена"}
            
            # Проверяем, что у пользователя есть активный заказ
            active_orders = await Order.get_active_orders_by_user(self.db_pool, user_id)
            if not active_orders:
                return {"success": False, "message": "У пользователя нет активных заказов"}
            
            # Берем первый активный заказ
            active_order = active_orders[0]
            
            # Получаем повербанк из заказа
            if not active_order.powerbank_id:
                return {"success": False, "message": "В заказе не указан повербанк"}
            
            powerbank = await Powerbank.get_by_id(self.db_pool, active_order.powerbank_id)
            if not powerbank:
                return {"success": False, "message": "Повербанк не найден"}
            
            # Обновляем статус повербанка в зависимости от типа ошибки
            new_status = 'user_reported_broken'
            write_off_reason = error_type if error_type in ['broken', 'lost', 'other'] else 'other'
            
            # Обновляем повербанк
            await powerbank.update_status(self.db_pool, new_status)
            await powerbank.update_write_off_reason(self.db_pool, write_off_reason)
            
            self.logger.info(f"Повербанк {powerbank.powerbank_id} помечен как {new_status} с причиной {write_off_reason}")
            
            return {
                "success": True,
                "message": "Возврат с поломкой инициирован",
                "powerbank_id": powerbank.powerbank_id,
                "error_type": error_type,
                "new_status": new_status,
                "write_off_reason": write_off_reason
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка инициации возврата с поломкой: {e}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    async def start_error_return_process(self, station_id: int, user_id: int, error_type_id: int = 1) -> Dict[str, Any]:
        """
        Инициирует процесс возврата повербанка с ошибкой и удерживает соединение
        
        Args:
            station_id: ID станции
            user_id: ID пользователя
            error_type_id: ID типа ошибки из таблицы powerbank_error
            
        Returns:
            Dict с результатом операции
        """
        try:
            self.logger.info(f"Инициация возврата с ошибкой: станция {station_id}, пользователь {user_id}, тип ошибки ID: {error_type_id}")
            
            # Валидируем тип ошибки
            try:
                powerbank_error = await PowerbankError.get_by_id(self.db_pool, error_type_id)
                if not powerbank_error:
                    return {"success": False, "message": f"Тип ошибки с ID {error_type_id} не найден"}
            except Exception as e:
                self.logger.error(f"Ошибка валидации типа ошибки: {e}")
                return {"success": False, "message": "Ошибка валидации типа ошибки"}
            
            # Проверяем, что станция существует и подключена
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"success": False, "message": "Станция не найдена"}
            
            # Проверяем соединение со станцией
            connection = self.connection_manager.get_connection_by_station_id(station_id)
            if not connection:
                return {"success": False, "message": "Станция не подключена"}
            
            # Проверяем, что у пользователя есть активный заказ
            active_orders = await Order.get_active_orders_by_user(self.db_pool, user_id)
            if not active_orders:
                return {"success": False, "message": "У пользователя нет активных заказов"}
            
            # Берем первый активный заказ
            active_order = active_orders[0]
            
            # Получаем повербанк из заказа
            if not active_order.powerbank_id:
                return {"success": False, "message": "В заказе не указан повербанк"}
            
            powerbank = await Powerbank.get_by_id(self.db_pool, active_order.powerbank_id)
            if not powerbank:
                return {"success": False, "message": "Повербанк не найден"}
            
            # Создаем отчет об аномалии
            try:
                await SlotAbnormalReport.create(
                    self.db_pool,
                    station_id=station_id,
                    slot_number=0,  # Будет обновлено при получении данных от станции
                    terminal_id=powerbank.serial_number,
                    event_type=str(error_type_id),
                    reported_at=datetime.now()
                )
                self.logger.info(f"Создан отчет об аномалии для станции {station_id}, повербанк {powerbank.serial_number}, тип ошибки: {powerbank_error.type_error}")
            except Exception as e:
                self.logger.error(f"Ошибка создания отчета об аномалии: {e}")
            
            # Создаем Future для ожидания ответа от станции
            future = asyncio.Future()
            return_key = f"{station_id}_{user_id}_{active_order.order_id}"
            
            # Сохраняем информацию о ожидающем возврате
            self.pending_error_returns[return_key] = {
                'future': future,
                'station_id': station_id,
                'user_id': user_id,
                'order_id': active_order.order_id,
                'powerbank_id': powerbank.powerbank_id,
                'error_type_id': error_type_id,
                'error_description': powerbank_error.type_error,
                'created_at': datetime.now()
            }
            
            self.logger.info(f"Ожидание возврата с ошибкой: {return_key}")
            
            # Ждем ответа от станции (максимум 30 секунд)
            try:
                result = await asyncio.wait_for(future, timeout=30.0)
                
                # Удаляем из ожидающих
                if return_key in self.pending_error_returns:
                    del self.pending_error_returns[return_key]
                
                return result
                
            except asyncio.TimeoutError:
                # Удаляем из ожидающих при таймауте
                if return_key in self.pending_error_returns:
                    del self.pending_error_returns[return_key]
                
                self.logger.error(f"Таймаут ожидания возврата с ошибкой: {return_key}")
                return {"success": False, "message": "Таймаут ожидания возврата от станции (30 секунд)"}
            
        except Exception as e:
            self.logger.error(f"Ошибка инициации возврата с ошибкой: {e}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    async def handle_error_return_response(self, data: bytes, connection) -> None:
        """
        Обрабатывает ответ станции на возврат с ошибкой
        
        Args:
            data: Данные от станции
            connection: Соединение со станцией
        """
        try:
            station_id = connection.station_id
            if not station_id:
                return
            
            # Ищем ожидающий возврат для этой станции
            pending_key = None
            for key, pending_data in self.pending_error_returns.items():
                if pending_data['station_id'] == station_id:
                    pending_key = key
                    break
            
            if not pending_key:
                self.logger.warning(f"Получен ответ на возврат с ошибкой от станции {station_id}, но нет ожидающих возвратов")
                return
            
            pending_data = self.pending_error_returns[pending_key]
            future = pending_data['future']
            
            if future.done():
                return
            
            # Парсим ответ от станции
            request = parse_return_power_bank_request(data)
            
            if 'error' in request:
                self.logger.error(f"Ошибка парсинга ответа на возврат с ошибкой: {request.get('error')}")
                future.set_result({"success": False, "message": "Ошибка парсинга ответа от станции"})
                return
            
            # Извлекаем данные из ответа
            slot = request.get('Slot', 0)
            terminal_id = request.get('TerminalID', '')
            level = request.get('Level', 0)
            voltage = request.get('Voltage', 0)
            current = request.get('Current', 0)
            temperature = request.get('Temperature', 0)
            status = request.get('Status', 0)
            soh = request.get('SOH', 100)
            
            self.logger.info(f"📥 Ответ на возврат с ошибкой: станция {station_id}, слот {slot}, TerminalID={terminal_id}")
            
            # Обновляем отчет об аномалии с информацией о слоте
            try:
                # Находим последний отчет для этой станции и повербанка
                reports = await SlotAbnormalReport.get_by_station_id(self.db_pool, station_id, limit=10)
                for report in reports:
                    if report.terminal_id == terminal_id and report.slot_number == 0:
                        # Обновляем слот в отчете
                        async with self.db_pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    "UPDATE slot_abnormal_reports SET slot_number = %s WHERE report_id = %s",
                                    (slot, report.report_id)
                                )
                        break
            except Exception as e:
                self.logger.error(f"Ошибка обновления отчета об аномалии: {e}")
            
            # Обновляем заказ на возврат
            try:
                await Order.update_order_status(
                    self.db_pool, pending_data['order_id'], 'return'
                )
                self.logger.info(f"Заказ {pending_data['order_id']} обновлен на возврат")
            except Exception as e:
                self.logger.error(f"Ошибка обновления заказа: {e}")
            
            # Добавляем повербанк в station_powerbank
            try:
                await StationPowerbank.add_powerbank(
                    self.db_pool,
                    station_id,
                    pending_data['powerbank_id'],
                    slot,
                    level=level,
                    voltage=voltage,
                    temperature=temperature
                )
                self.logger.info(f"Повербанк {terminal_id} добавлен в station_powerbank (станция {station_id}, слот {slot})")
            except Exception as e:
                self.logger.error(f"Ошибка добавления в station_powerbank: {e}")
            
            # Обновляем данные станции
            try:
                station = await Station.get_by_id(self.db_pool, station_id)
                if station:
                    await station.update_last_seen(self.db_pool)
                    new_remain = int(station.remain_num) + 1
                    await station.update_remain_num(self.db_pool, new_remain)
                    self.logger.info(f"Станция {station_id}: remain_num {station.remain_num} → {new_remain}")
            except Exception as e:
                self.logger.error(f"Ошибка обновления станции: {e}")
            
            # Уведомляем о успешном возврате
            future.set_result({
                "success": True,
                "message": "Возврат с ошибкой успешно обработан",
                "station_id": station_id,
                "slot": slot,
                "terminal_id": terminal_id,
                "powerbank_id": pending_data['powerbank_id'],
                "order_id": pending_data['order_id'],
                "error_type_id": pending_data.get('error_type_id'),
                "error_description": pending_data.get('error_description')
            })
            
            self.logger.info(f"✅ Возврат с ошибкой успешно обработан для станции {station_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки ответа на возврат с ошибкой: {e}")
            # Уведомляем об ошибке
            if pending_key and pending_key in self.pending_error_returns:
                future = self.pending_error_returns[pending_key]['future']
                if not future.done():
                    future.set_result({"success": False, "message": f"Ошибка обработки: {str(e)}"})