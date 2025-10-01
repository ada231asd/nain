"""
Модель для работы с повербанками в станциях
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import aiomysql
from utils.packet_utils import get_moscow_time


class StationPowerbank:
    """Модель для работы с повербанками в станциях"""
    
    def __init__(self, id: int = None, station_id: int = None, powerbank_id: int = None,
                 slot_number: int = None, level: int = None, voltage: int = None,
                 temperature: int = None, last_update: datetime = None):
        self.id = id
        self.station_id = station_id
        self.powerbank_id = powerbank_id
        self.slot_number = slot_number
        self.level = level
        self.voltage = voltage
        self.temperature = temperature
        self.last_update = last_update or get_moscow_time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь"""
        return {
            'id': self.id,
            'station_id': self.station_id,
            'powerbank_id': self.powerbank_id,
            'slot_number': self.slot_number,
            'level': self.level,
            'voltage': self.voltage,
            'temperature': self.temperature,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    @classmethod
    async def get_by_station(cls, db_pool, station_id: int) -> List['StationPowerbank']:
        """Получает все повербанки в станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM station_powerbank 
                    WHERE station_id = %s 
                    ORDER BY slot_number
                """, (station_id,))
                results = await cur.fetchall()
                
                return [cls(
                    id=row['id'],
                    station_id=row['station_id'],
                    powerbank_id=row['powerbank_id'],
                    slot_number=row['slot_number'],
                    level=row['level'],
                    voltage=row['voltage'],
                    temperature=row['temperature'],
                    last_update=row['last_update']
                ) for row in results]

    @classmethod
    async def get_station_powerbanks(cls, db_pool, station_id: int) -> List['StationPowerbank']:
        """Получает все повербанки в станции (алиас для get_by_station)"""
        return await cls.get_by_station(db_pool, station_id)
    
    @classmethod
    async def get_by_station_id(cls, db_pool, station_id: int) -> Optional['StationPowerbank']:
        """Получает первый повербанк в станции (для извлечения)"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM station_powerbank 
                    WHERE station_id = %s 
                    LIMIT 1
                """, (station_id,))
                result = await cur.fetchone()
                
                if result:
                    return cls(
                        id=int(result['id']),
                        station_id=int(result['station_id']),
                        powerbank_id=int(result['powerbank_id']),
                        slot_number=int(result['slot_number']),
                        level=int(result['level']) if result['level'] else None,
                        voltage=int(result['voltage']) if result['voltage'] else None,
                        temperature=int(result['temperature']) if result['temperature'] else None,
                        last_update=result['last_update']
                    )
                return None
    
    @classmethod
    async def get_by_slot(cls, db_pool, station_id: int, slot_number: int) -> Optional['StationPowerbank']:
        """Получает повербанк в конкретном слоте станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM station_powerbank 
                    WHERE station_id = %s AND slot_number = %s
                """, (station_id, slot_number))
                result = await cur.fetchone()
                
                if result:
                    return cls(
                        id=int(result['id']),
                        station_id=int(result['station_id']),
                        powerbank_id=int(result['powerbank_id']),
                        slot_number=int(result['slot_number']),
                        level=int(result['level']) if result['level'] else None,
                        voltage=int(result['voltage']) if result['voltage'] else None,
                        temperature=int(result['temperature']) if result['temperature'] else None,
                        last_update=result['last_update']
                    )
                return None

    @classmethod
    async def get_by_powerbank_id(cls, db_pool, powerbank_id: int) -> Optional['StationPowerbank']:
        """Получает повербанк по его ID в любой станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM station_powerbank 
                    WHERE powerbank_id = %s
                """, (powerbank_id,))
                result = await cur.fetchone()
                
                if result:
                    return cls(
                        id=int(result['id']),
                        station_id=int(result['station_id']),
                        powerbank_id=int(result['powerbank_id']),
                        slot_number=int(result['slot_number']),
                        level=int(result['level']) if result['level'] else None,
                        voltage=int(result['voltage']) if result['voltage'] else None,
                        temperature=int(result['temperature']) if result['temperature'] else None,
                        last_update=result['last_update']
                    )
                return None
    
    @classmethod
    async def add_powerbank(cls, db_pool, station_id: int, powerbank_id: int, 
                           slot_number: int, level: int = None, voltage: int = None, 
                           temperature: int = None) -> 'StationPowerbank':
        """Добавляет повербанк в станцию"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Конвертируем значения в int, чтобы избежать MySQL warnings
                level_int = int(level) if level is not None else None
                voltage_int = int(voltage) if voltage is not None else None
                temperature_int = int(temperature) if temperature is not None else None
                
                # Используем INSERT ... ON DUPLICATE KEY UPDATE для избежания дубликатов
                await cur.execute("""
                    INSERT INTO station_powerbank 
                    (station_id, powerbank_id, slot_number, level, voltage, temperature, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW()) AS new_values
                    ON DUPLICATE KEY UPDATE
                    powerbank_id = new_values.powerbank_id,
                    level = new_values.level,
                    voltage = new_values.voltage,
                    temperature = new_values.temperature,
                    last_update = NOW()
                """, (station_id, powerbank_id, slot_number, level_int, voltage_int, temperature_int))
                
                # Получаем ID записи (новой или обновленной)
                await cur.execute("""
                    SELECT id FROM station_powerbank 
                    WHERE station_id = %s AND slot_number = %s
                """, (station_id, slot_number))
                result = await cur.fetchone()
                record_id = result[0] if result else cur.lastrowid
                
                return cls(
                    id=record_id,
                    station_id=station_id,
                    powerbank_id=powerbank_id,
                    slot_number=slot_number,
                    level=level,
                    voltage=voltage,
                    temperature=temperature,
                    last_update=get_moscow_time()
                )
    
    @classmethod
    async def remove_powerbank(cls, db_pool, station_id: int, slot_number: int) -> bool:
        """Удаляет повербанк из станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                result = await cur.execute("""
                    DELETE FROM station_powerbank 
                    WHERE station_id = %s AND slot_number = %s
                """, (station_id, slot_number))
                return result > 0
    
    @classmethod
    async def remove_powerbank_by_id(cls, db_pool, station_id: int, powerbank_id: int) -> bool:
        """Удаляет конкретный повербанк из станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                result = await cur.execute("""
                    DELETE FROM station_powerbank 
                    WHERE station_id = %s AND powerbank_id = %s
                """, (station_id, powerbank_id))
                return result > 0
    
    @classmethod
    async def clear_station_powerbanks(cls, db_pool, station_id: int) -> int:
        """Очищает все повербанки из станции (принудительное извлечение)"""
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    result = await cur.execute("""
                        DELETE FROM station_powerbank 
                        WHERE station_id = %s
                    """, (station_id,))
                    return result
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return 0
    
    @classmethod
    async def update_powerbank_data(cls, db_pool, station_id: int, slot_number: int,
                                   level: int = None, voltage: int = None, 
                                   temperature: int = None) -> bool:
        """Обновляет данные повербанка в станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Строим запрос динамически
                updates = []
                params = []
                
                if level is not None:
                    updates.append("level = %s")
                    params.append(int(level))
                if voltage is not None:
                    updates.append("voltage = %s")
                    params.append(int(voltage))
                if temperature is not None:
                    updates.append("temperature = %s")
                    params.append(int(temperature))
                
                if not updates:
                    return False
                
                updates.append("last_update = NOW()")
                params.extend([station_id, slot_number])
                
                query = f"""
                    UPDATE station_powerbank 
                    SET {', '.join(updates)}
                    WHERE station_id = %s AND slot_number = %s
                """
                
                result = await cur.execute(query, params)
                return result > 0
    
    @classmethod
    async def clear_station(cls, db_pool, station_id: int) -> bool:
        """Очищает все повербанки из станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                result = await cur.execute("""
                    DELETE FROM station_powerbank WHERE station_id = %s
                """, (station_id,))
                return result > 0
    
    @classmethod
    async def sync_station_powerbanks(cls, db_pool, station_id: int, slots_data: list) -> None:
        """
        Синхронизирует повербанки в станции с данными из пакета логина
        Удаляет старые записи и добавляет ВСЕ повербанки (независимо от статуса)
        """
        
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Очищаем старые данные
                await cur.execute("DELETE FROM station_powerbank WHERE station_id = %s", (station_id,))
                
                added_count = 0
                
                # Добавляем ВСЕ повербанки (независимо от статуса)
                for slot in slots_data:
                    terminal_id = slot.get('TerminalID')
                    
                    if not terminal_id or terminal_id == '0000000000000000':
                        continue  # Пропускаем пустые слоты
                    
                    # Получаем powerbank_id по serial_number
                    await cur.execute("""
                        SELECT id FROM powerbank WHERE serial_number = %s
                    """, (terminal_id,))
                    powerbank_result = await cur.fetchone()
                    
                    if powerbank_result:
                        powerbank_id = powerbank_result[0]
                        
                        # Добавляем в station_powerbank 
                       
                        level = int(slot.get('Level', 0)) if slot.get('Level') is not None else None
                        voltage = int(slot.get('Voltage', 0)) if slot.get('Voltage') is not None else None
                        temperature = int(slot.get('Temp', 0)) if slot.get('Temp') is not None else None
                        
                        await cur.execute("""
                            INSERT INTO station_powerbank 
                            (station_id, powerbank_id, slot_number, level, voltage, temperature, last_update)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW()) AS new_values
                            ON DUPLICATE KEY UPDATE
                            powerbank_id = new_values.powerbank_id,
                            level = new_values.level,
                            voltage = new_values.voltage,
                            temperature = new_values.temperature,
                            last_update = NOW()
                        """, (
                            station_id,
                            powerbank_id,
                            int(slot['Slot']),
                            level,
                            voltage,
                            temperature
                        ))
                        
                        added_count += 1
                    # else: повербанк не найден - пропускаем
    
    async def update_data(self, db_pool, level: int = None, voltage: int = None, 
                         temperature: int = None) -> bool:
        """Обновляет данные конкретного повербанка"""
        return await StationPowerbank.update_powerbank_data(
            db_pool, self.station_id, self.slot_number, level, voltage, temperature
        )
    
    @classmethod
    async def get_by_station_and_slot(cls, db_pool, station_id: int, slot_number: int) -> Optional['StationPowerbank']:
        """Получает повербанк по станции и слоту"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, station_id, powerbank_id, slot_number, level, voltage, temperature, last_update
                    FROM station_powerbank 
                    WHERE station_id = %s AND slot_number = %s
                """, (station_id, slot_number))
                
                result = await cursor.fetchone()
                
                if result:
                    return cls(
                        id=result[0],
                        station_id=result[1],
                        powerbank_id=result[2],
                        slot_number=result[3],
                        level=result[4],
                        voltage=result[5],
                        temperature=result[6],
                        last_update=result[7]
                    )
                return None
    
    @classmethod
    async def update_or_add_powerbank(cls, db_pool, station_id: int, powerbank_id: int, 
                                    slot_number: int, level: int = None, voltage: int = None, 
                                    temperature: int = None) -> bool:
        """Обновляет существующий повербанк в слоте или добавляет новый"""
        try:
            # Проверяем, есть ли уже повербанк в этом слоте
            existing = await cls.get_by_station_and_slot(db_pool, station_id, slot_number)
            
            if existing:
                # Обновляем существующий повербанк
                return await cls.update_powerbank_data(
                    db_pool, 
                    station_id, 
                    slot_number, 
                    level=level, 
                    voltage=voltage, 
                    temperature=temperature
                )
            else:
                # Добавляем новый повербанк в станцию
                return await cls.add_powerbank(
                    db_pool, 
                    station_id, 
                    powerbank_id, 
                    slot_number, 
                    level=level, 
                    voltage=voltage, 
                    temperature=temperature
                )
        except Exception as e:
            print(f"Ошибка update_or_add_powerbank: {e}")
            return False
    
    @classmethod
    async def get_occupied_slots(cls, db_pool, station_id: int) -> List[int]:
        """Получает список занятых слотов в станции"""
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT slot_number 
                        FROM station_powerbank 
                        WHERE station_id = %s
                    """, (station_id,))
                    
                    results = await cur.fetchall()
                    return [row[0] for row in results]
                    
        except Exception as e:
            print(f"Ошибка получения занятых слотов: {e}")
            return []
