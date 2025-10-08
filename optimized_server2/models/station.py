"""
Модель станции
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiomysql
from utils.time_utils import get_moscow_time


class Station:
    """Модель станции"""
    
    def __init__(self, station_id: int, box_id: str, slots_declared: int, 
                 remain_num: int, status: str, org_unit_id: int = 1,
                 iccid: Optional[str] = None, address_id: Optional[int] = None,
                 last_seen: Optional[datetime] = None, created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None):
        self.station_id = station_id
        self.box_id = box_id
        self.slots_declared = slots_declared
        self.remain_num = remain_num
        self.status = status
        self.org_unit_id = org_unit_id
        self.iccid = iccid
        self.address_id = address_id
        self.last_seen = last_seen
        self.created_at = created_at or get_moscow_time()
        self.updated_at = updated_at or get_moscow_time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует станцию в словарь"""
        return {
            'station_id': self.station_id,
            'box_id': self.box_id,
            'slots_declared': self.slots_declared,
            'remain_num': self.remain_num,
            'status': self.status,
            'org_unit_id': self.org_unit_id,
            'iccid': self.iccid,
            'address_id': self.address_id,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    async def get_by_id(cls, pool, station_id: int) -> Optional['Station']:
        """Получает станцию по ID"""
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM station WHERE station_id=%s", (station_id,))
                station_data = await cur.fetchone()
                
                if station_data:
                    # Нормализуем datetime поля к московскому времени
                    from utils.time_utils import normalize_datetime_to_moscow
                    
                    return cls(
                        station_id=int(station_data["station_id"]),
                        box_id=str(station_data["box_id"]),
                        slots_declared=int(station_data["slots_declared"]),
                        remain_num=int(station_data["remain_num"]),
                        status=str(station_data["status"]),
                        org_unit_id=int(station_data["org_unit_id"]),
                        iccid=station_data.get("iccid"),
                        address_id=station_data.get("address_id"),
                        last_seen=normalize_datetime_to_moscow(station_data.get("last_seen")),
                        created_at=normalize_datetime_to_moscow(station_data.get("created_at")),
                        updated_at=normalize_datetime_to_moscow(station_data.get("updated_at"))
                    )
                return None
    
    @classmethod
    async def get_or_create(cls, pool, box_id: str, slots_declared: int) -> tuple['Station', Optional[bytes]]:
        """
        Получает или создает станцию
        """
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Проверяем существующую станцию
                await cur.execute("SELECT * FROM station WHERE box_id=%s", (box_id,))
                station_data = await cur.fetchone()
                
                if not station_data:
                    # Станции нет — создаем со статусом pending
                    await cur.execute("""
                        INSERT INTO station (org_unit_id, box_id, slots_declared, remain_num, status)
                        VALUES (1, %s, %s, %s, 'pending')
                    """, (box_id, slots_declared, slots_declared))
                    
                    station_id = cur.lastrowid
                    station_data = {
                        "station_id": station_id,
                        "box_id": box_id,
                        "slots_declared": slots_declared,
                        "remain_num": slots_declared,
                        "status": "pending",
                        "org_unit_id": 1
                    }
                else:
                    # Станция существует, проверяем группу
                    if station_data["org_unit_id"] is None:
                        await cur.execute("UPDATE station SET org_unit_id = 1 WHERE station_id = %s", 
                                        (station_data["station_id"],))
                        station_data["org_unit_id"] = 1
                
                # Получаем секретный ключ
                await cur.execute("SELECT key_value FROM station_secret_key WHERE station_id=%s", 
                                (station_data["station_id"],))
                key_row = await cur.fetchone()
                secret_key = key_row["key_value"] if key_row else None
                
                station = cls(
                    station_id=int(station_data["station_id"]),
                    box_id=str(station_data["box_id"]),
                    slots_declared=int(station_data["slots_declared"]),
                    remain_num=int(station_data["remain_num"]),
                    status=str(station_data["status"]),
                    org_unit_id=int(station_data["org_unit_id"]),
                    iccid=station_data.get("iccid"),
                    address_id=station_data.get("address_id")
                )
                
                return station, secret_key
    
    async def update_status(self, pool, new_status: str) -> None:
        """Обновляет статус станции"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                moscow_time = get_moscow_time()
                await cur.execute(
                    "UPDATE station SET status = %s, updated_at = %s WHERE station_id = %s",
                    (new_status, moscow_time, self.station_id)
                )
                self.status = new_status
                self.updated_at = get_moscow_time()
    
    async def update_last_seen(self, pool) -> None:
        """Обновляет время последнего контакта"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                moscow_time = get_moscow_time()
                await cur.execute(
                    "UPDATE station SET last_seen = %s, updated_at = %s WHERE station_id = %s",
                    (moscow_time, moscow_time, self.station_id)
                )
                self.last_seen = moscow_time
                self.updated_at = moscow_time
    
    async def update_remain_num(self, pool, remain_num: int) -> None:
        """Обновляет количество свободных слотов"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                moscow_time = get_moscow_time()
                await cur.execute(
                    "UPDATE station SET remain_num = %s, updated_at = %s WHERE station_id = %s",
                    (remain_num, moscow_time, self.station_id)
                )
                self.remain_num = remain_num
                self.updated_at = moscow_time
    
    async def update_iccid(self, pool, iccid: str) -> None:
        """Обновляет ICCID станции"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                moscow_time = get_moscow_time()
                await cur.execute(
                    "UPDATE station SET iccid = %s, updated_at = %s WHERE station_id = %s",
                    (iccid, moscow_time, self.station_id)
                )
                self.iccid = iccid
                self.updated_at = moscow_time

    @classmethod
    async def get_all_active(cls, db_pool) -> list:
        """Получает все активные станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT station_id, box_id, iccid, slots_declared, remain_num, status, last_seen, org_unit_id, created_at, updated_at "
                    "FROM station WHERE status = 'active' ORDER BY created_at DESC"
                )
                results = await cursor.fetchall()
                
                stations = []
                for result in results:
                    # Нормализуем datetime поля к московскому времени
                    from utils.time_utils import normalize_datetime_to_moscow
                    
                    stations.append(cls(
                        station_id=int(result[0]),
                        box_id=str(result[1]),
                        iccid=str(result[2]) if result[2] else None,
                        slots_declared=int(result[3]) if result[3] else 0,
                        remain_num=int(result[4]) if result[4] else 0,
                        status=str(result[5]),
                        last_seen=normalize_datetime_to_moscow(result[6]),
                        org_unit_id=int(result[7]) if result[7] else None,
                        created_at=normalize_datetime_to_moscow(result[8]),
                        updated_at=normalize_datetime_to_moscow(result[9])
                    ))
                return stations
    
    @classmethod
    async def get_all(cls, db_pool) -> List['Station']:
        """Получает все станции"""
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT station_id, box_id, iccid, slots_declared, remain_num, status, last_seen, org_unit_id, created_at, updated_at "
                    "FROM station ORDER BY created_at DESC"
                )
                results = await cursor.fetchall()
                
                stations = []
                for result in results:
                    # Нормализуем datetime поля к московскому времени
                    from utils.time_utils import normalize_datetime_to_moscow
                    
                    stations.append(cls(
                        station_id=int(result[0]),
                        box_id=str(result[1]),
                        iccid=str(result[2]) if result[2] else None,
                        slots_declared=int(result[3]) if result[3] else 0,
                        remain_num=int(result[4]) if result[4] else 0,
                        status=str(result[5]),
                        last_seen=normalize_datetime_to_moscow(result[6]),
                        org_unit_id=int(result[7]) if result[7] else None,
                        created_at=normalize_datetime_to_moscow(result[8]),
                        updated_at=normalize_datetime_to_moscow(result[9])
                    ))
                return stations
    
