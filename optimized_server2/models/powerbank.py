"""
Модель для работы с повербанками
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from utils.time_utils import get_moscow_time
from utils.centralized_logger import get_logger

logger = get_logger('powerbank')


class Powerbank:
    """Модель повербанка"""
    
    def __init__(self, powerbank_id: int = None, org_unit_id: int = None, 
                 serial_number: str = None, soh: int = None, 
                 status: str = 'unknown', write_off_reason: str = 'none',
                 created_at: datetime = None):
        self.powerbank_id = powerbank_id
        self.org_unit_id = org_unit_id
        self.serial_number = serial_number
        self.soh = soh
        self.status = status
        self.write_off_reason = write_off_reason
        self.created_at = created_at
    
    @classmethod
    async def get_by_id(cls, db_pool, powerbank_id: int) -> Optional['Powerbank']:
        """Получает повербанк по ID"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, org_unit_id, serial_number, soh, status, write_off_reason, created_at "
                    "FROM powerbank WHERE id = %s",
                    (powerbank_id,)
                )
                result = await cursor.fetchone()
                
                if result:
                    return cls(
                        powerbank_id=int(result[0]),
                        org_unit_id=int(result[1]) if result[1] else None,
                        serial_number=str(result[2]),
                        soh=int(result[3]) if result[3] else None,
                        status=str(result[4]),
                        write_off_reason=str(result[5]) if result[5] else None,
                        created_at=result[6]
                    )
                return None

    @classmethod
    async def get_by_serial(cls, db_pool, serial_number: str) -> Optional['Powerbank']:
        """Получает повербанк по серийному номеру"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, org_unit_id, serial_number, soh, status, write_off_reason, created_at "
                    "FROM powerbank WHERE serial_number = %s",
                    (serial_number,)
                )
                result = await cursor.fetchone()
                
                if result:
                    return cls(
                        powerbank_id=int(result[0]),
                        org_unit_id=int(result[1]) if result[1] else None,
                        serial_number=str(result[2]),
                        soh=int(result[3]) if result[3] else None,
                        status=str(result[4]),
                        write_off_reason=str(result[5]) if result[5] else None,
                        created_at=result[6]
                    )
                return None
    
    @classmethod
    async def get_by_serial_number(cls, db_pool, serial_number: str) -> Optional['Powerbank']:
        """Получает повербанк по серийному номеру"""
        return await cls.get_by_serial(db_pool, serial_number)
    
    @classmethod
    async def create_unknown(cls, db_pool, serial_number: str, org_unit_id: int = None) -> 'Powerbank':
        """Создает повербанк со статусом unknown"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO powerbank (org_unit_id, serial_number, soh, status, write_off_reason, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (org_unit_id, serial_number, 0, 'unknown', 'none', get_moscow_time())
                )
                powerbank_id = cursor.lastrowid
                
                return cls(
                    powerbank_id=powerbank_id,
                    org_unit_id=org_unit_id,
                    serial_number=serial_number,
                    soh=0,
                    status='unknown',
                    write_off_reason='none',
                    created_at=get_moscow_time()
                )
    
    @classmethod
    async def create_active(cls, db_pool, serial_number: str, org_unit_id: int, soh: int = 100) -> 'Powerbank':
        """Создает повербанк со статусом active"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO powerbank (org_unit_id, serial_number, soh, status, write_off_reason, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                        (org_unit_id, serial_number, soh, 'active', 'none', get_moscow_time())
                )
                powerbank_id = cursor.lastrowid
                
                return cls(
                    powerbank_id=powerbank_id,
                    org_unit_id=org_unit_id,
                    serial_number=serial_number,
                    soh=soh,
                    status='active',
                    write_off_reason='none',
                    created_at=get_moscow_time()
                )
    
    @classmethod
    async def create(cls, db_pool, org_unit_id: int, serial_number: str, soh: int, status: str) -> Optional['Powerbank']:
        """Создает повербанк с указанными параметрами"""
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO powerbank (org_unit_id, serial_number, soh, status, write_off_reason, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (org_unit_id, serial_number, soh, status, 'none', get_moscow_time())
                    )
                    powerbank_id = cursor.lastrowid
                    
                    return cls(
                        powerbank_id=powerbank_id,
                        org_unit_id=org_unit_id,
                        serial_number=serial_number,
                        soh=soh,
                        status=status,
                        write_off_reason='none',
                        created_at=get_moscow_time()
                    )
        except Exception as e:
            logger.error(f"Ошибка создания повербанка: {e}")
            return None
    
    async def update_status(self, db_pool, new_status: str) -> bool:
        """Обновляет статус повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE powerbank SET status = %s WHERE id = %s",
                    (str(new_status), int(self.powerbank_id))
                )
                self.status = new_status
                return True
    
    async def update_write_off_reason(self, db_pool, new_reason: str) -> bool:
        """Обновляет причину списания повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE powerbank SET write_off_reason = %s WHERE id = %s",
                    (str(new_reason), int(self.powerbank_id))
                )
                self.write_off_reason = new_reason
                return True
    
    async def update_soh(self, db_pool, soh: int) -> bool:
        """Обновляет SOH повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE powerbank SET soh = %s WHERE id = %s",
                    (int(soh) if soh is not None else None, int(self.powerbank_id))
                )
                self.soh = soh
                return True
    
    async def update_status_and_soh(self, db_pool, new_status: str, soh: int) -> bool:
        """Обновляет статус и SOH повербанка"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE powerbank SET status = %s, soh = %s WHERE id = %s",
                    (str(new_status), int(soh) if soh is not None else None, int(self.powerbank_id))
                )
                self.status = new_status
                self.soh = soh
                return True
    
    
    @classmethod
    async def get_by_terminal_id(cls, db_pool, terminal_id: str) -> Optional['Powerbank']:
        """Получает повербанк по terminal_id станции."""
        if not terminal_id:
            return None
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, org_unit_id, serial_number, soh, status, write_off_reason, created_at "
                    "FROM powerbank WHERE serial_number = %s LIMIT 1",
                    (terminal_id,)
                )
                result = await cursor.fetchone()
                if result:
                    return cls(
                        powerbank_id=int(result[0]),
                        org_unit_id=int(result[1]) if result[1] else None,
                        serial_number=str(result[2]),
                        soh=int(result[3]) if result[3] else None,
                        status=str(result[4]),
                        write_off_reason=str(result[5]) if result[5] else None,
                        created_at=result[6]
                    )
                return None

    async def update_power_er(self, db_pool, error_type: int) -> bool:
        """Устанавливает тип ошибки (power_er) для повербанка."""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Явно преобразуем error_type в int, если это не None
                error_value = int(error_type) if error_type is not None else None
                await cursor.execute(
                    "UPDATE powerbank SET power_er = %s WHERE id = %s",
                    (error_value, int(self.powerbank_id))
                )
                return True

    @classmethod
    async def get_powerbank_status_changes(cls, db_pool, station_id: int) -> Dict[int, str]:
        """
        Получает изменения статусов повербанков в станции
        Возвращает словарь {powerbank_id: new_status}
        """
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Получаем все повербанки в станции с их текущими статусами
                await cursor.execute("""
                    SELECT sp.powerbank_id, p.status, p.serial_number
                    FROM station_powerbank sp
                    JOIN powerbank p ON sp.powerbank_id = p.id
                    WHERE sp.station_id = %s
                """, (station_id,))
                
                results = await cursor.fetchall()
                status_changes = {}
                
                for powerbank_id, status, serial_number in results:
                    status_changes[powerbank_id] = status
                    print(f"Повербанк {serial_number} (ID: {powerbank_id}) имеет статус: {status}")
                
                return status_changes

    @classmethod
    async def get_all_active(cls, db_pool) -> list:
        """Получает все активные повербанки"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, org_unit_id, serial_number, soh, status, write_off_reason, created_at "
                    "FROM powerbank WHERE status = 'active' ORDER BY created_at DESC"
                )
                results = await cursor.fetchall()
                
                powerbanks = []
                for result in results:
                    powerbanks.append(cls(
                        powerbank_id=int(result[0]),
                        org_unit_id=int(result[1]) if result[1] else None,
                        serial_number=str(result[2]),
                        soh=int(result[3]) if result[3] else None,
                        status=str(result[4]),
                        write_off_reason=str(result[5]) if result[5] else None,
                        created_at=result[6]
                    ))
                return powerbanks

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            'powerbank_id': self.powerbank_id,
            'org_unit_id': self.org_unit_id,
            'serial_number': self.serial_number,
            'soh': self.soh,
            'status': self.status,
            'write_off_reason': self.write_off_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
