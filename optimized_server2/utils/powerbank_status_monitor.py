"""
Утилита для мониторинга изменений статусов повербанков
"""
from typing import Dict, List, Set
from datetime import datetime
import asyncio


class PowerbankStatusMonitor:
    """Монитор изменений статусов повербанков"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.status_cache: Dict[int, str] = {}  # Кэш статусов повербанков
        self.station_powerbanks: Dict[int, Set[int]] = {}  # Повербанки в станциях
    
    async def initialize_station(self, station_id: int) -> None:
        """Инициализирует мониторинг для станции"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем все повербанки в станции
                    await cur.execute("""
                        SELECT sp.powerbank_id, p.status
                        FROM station_powerbank sp
                        JOIN powerbank p ON sp.powerbank_id = p.id
                        WHERE sp.station_id = %s
                    """, (station_id,))
                    
                    results = await cur.fetchall()
                    powerbank_ids = set()
                    
                    for powerbank_id, status in results:
                        self.status_cache[powerbank_id] = status
                        powerbank_ids.add(powerbank_id)
                    
                    self.station_powerbanks[station_id] = powerbank_ids
                    print(f"Инициализирован мониторинг для станции {station_id}: {len(powerbank_ids)} повербанков")
                    
        except Exception as e:
            print(f"Ошибка инициализации мониторинга для станции {station_id}: {e}")
    
    async def check_status_changes(self, station_id: int) -> Dict[int, str]:
        """Проверяет изменения статусов повербанков в станции"""
        try:
            if station_id not in self.station_powerbanks:
                await self.initialize_station(station_id)
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Получаем текущие статусы повербанков в станции
                    await cur.execute("""
                        SELECT sp.powerbank_id, p.status, p.serial_number
                        FROM station_powerbank sp
                        JOIN powerbank p ON sp.powerbank_id = p.id
                        WHERE sp.station_id = %s
                    """, (station_id,))
                    
                    results = await cur.fetchall()
                    status_changes = {}
                    
                    for powerbank_id, current_status, serial_number in results:
                        old_status = self.status_cache.get(powerbank_id)
                        
                        if old_status != current_status:
                            status_changes[powerbank_id] = current_status
                            self.status_cache[powerbank_id] = current_status
                            print(f"Изменение статуса повербанка {serial_number} (ID: {powerbank_id}): {old_status} -> {current_status}")
                    
                    return status_changes
                    
        except Exception as e:
            print(f"Ошибка проверки изменений статусов для станции {station_id}: {e}")
            return {}
    
    async def handle_status_change(self, station_id: int, powerbank_id: int, new_status: str) -> None:
        """Обрабатывает изменение статуса повербанка"""
        try:
            if new_status == 'active':
                # Повербанк стал активным - можно оставить в station_powerbank
                print(f"Повербанк {powerbank_id} стал активным - остается в станции {station_id}")
            elif new_status in ['user_reported_broken', 'system_error', 'written_off']:
                # Повербанк стал неактивным - нужно извлечь из станции
                print(f"Повербанк {powerbank_id} стал неактивным ({new_status}) - требуется извлечение из станции {station_id}")
                await self._schedule_powerbank_ejection(station_id, powerbank_id)
            elif new_status == 'unknown':
                # Повербанк стал неизвестным - остается в станции до активации
                print(f"Повербанк {powerbank_id} стал неизвестным - остается в станции {station_id} до активации")
                
        except Exception as e:
            print(f"Ошибка обработки изменения статуса повербанка {powerbank_id}: {e}")
    
    async def _schedule_powerbank_ejection(self, station_id: int, powerbank_id: int) -> None:
        """Планирует извлечение неактивного повербанка"""
        try:
            # Получаем информацию о слоте повербанка
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT slot_number FROM station_powerbank 
                        WHERE station_id = %s AND powerbank_id = %s
                    """, (station_id, powerbank_id))
                    
                    result = await cur.fetchone()
                    if result:
                        slot_number = result[0]
                        print(f"Запланировано извлечение повербанка {powerbank_id} из слота {slot_number} станции {station_id}")
                        
                        # Здесь можно добавить логику отправки команды на извлечение
                        # или поставить задачу в очередь
                        
        except Exception as e:
            print(f"Ошибка планирования извлечения повербанка {powerbank_id}: {e}")
    
    async def monitor_station(self, station_id: int, interval_seconds: int = 30) -> None:
        """Запускает мониторинг станции в фоновом режиме"""
        print(f"Запуск мониторинга станции {station_id} с интервалом {interval_seconds} секунд")
        
        while True:
            try:
                status_changes = await self.check_status_changes(station_id)
                
                for powerbank_id, new_status in status_changes.items():
                    await self.handle_status_change(station_id, powerbank_id, new_status)
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                print(f"Ошибка мониторинга станции {station_id}: {e}")
                await asyncio.sleep(interval_seconds)
    
    def get_station_powerbanks(self, station_id: int) -> Set[int]:
        """Получает список повербанков в станции"""
        return self.station_powerbanks.get(station_id, set())
    
    def get_powerbank_status(self, powerbank_id: int) -> str:
        """Получает текущий статус повербанка"""
        return self.status_cache.get(powerbank_id, 'unknown')
