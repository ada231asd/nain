from typing import Optional, Dict, Any
import struct

from models.station_powerbank import StationPowerbank
from models.powerbank import Powerbank
from models.order import Order
from models.station import Station
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
