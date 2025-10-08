"""
API для административных операций с повербанками
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.time_utils import get_moscow_time
import aiomysql

from models.powerbank import Powerbank
from models.station_powerbank import StationPowerbank



class AdminPowerbankAPI:
    """API для административных операций с повербанками"""
    
    def __init__(self, db_pool, connection_manager=None):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def get_unknown_powerbanks(self) -> List[Dict[str, Any]]:
        """Получает список повербанков со статусом unknown"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT p.id, p.serial_number, p.soh, p.org_unit_id, p.created_at,
                               ou.name as org_unit_name
                        FROM powerbank p
                        LEFT JOIN org_unit ou ON p.org_unit_id = ou.org_unit_id
                        WHERE p.status = 'unknown'
                        ORDER BY p.created_at DESC
                    """)
                    
                    powerbanks = await cur.fetchall()
                    return [dict(row) for row in powerbanks]
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return []
    
    async def activate_powerbank(self, powerbank_id: int, admin_user_id: int, target_org_unit_id: int = None) -> Dict[str, Any]:
        """Активирует повербанк"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Проверяем, что повербанк существует и имеет статус unknown
                    await cur.execute("""
                        SELECT id, serial_number, status, org_unit_id 
                        FROM powerbank WHERE id = %s AND status = 'unknown'
                    """, (powerbank_id,))
                    
                    powerbank_data = await cur.fetchone()
                    if not powerbank_data:
                        return {
                            "success": False,
                            "message": "Повербанк не найден или уже активирован"
                        }
                    
                    # Если указана целевая группа, перемещаем повербанк
                    if target_org_unit_id:
                        await cur.execute("""
                            UPDATE powerbank 
                            SET status = 'active', org_unit_id = %s, updated_at = %s
                            WHERE id = %s
                        """, (target_org_unit_id, get_moscow_time(), powerbank_id))
                    else:
                        # Оставляем в текущей группе
                        await cur.execute("""
                            UPDATE powerbank 
                            SET status = 'active', updated_at = %s
                            WHERE id = %s
                        """, (get_moscow_time(), powerbank_id))
                    
                    # Синхронизируем со станциями
                    await self._sync_activated_powerbank_to_stations(powerbank_id)
                    
                    return {
                        "success": True,
                        "message": f"Повербанк {powerbank_data[1]} активирован",
                        "powerbank_id": powerbank_id,
                        "admin_user_id": admin_user_id,
                        "activated_at": get_moscow_time().isoformat()
                    }
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка активации: {str(e)}"
            }
    
    async def deactivate_powerbank(self, powerbank_id: int, admin_user_id: int, reason: str = "admin_deactivated") -> Dict[str, Any]:
        """Деактивирует повербанк"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Проверяем, что повербанк существует
                    await cur.execute("""
                        SELECT id, serial_number, status 
                        FROM powerbank WHERE id = %s
                    """, (powerbank_id,))
                    
                    powerbank_data = await cur.fetchone()
                    if not powerbank_data:
                        return {
                            "success": False,
                            "message": "Повербанк не найден"
                        }
                    
                    # Деактивируем повербанк
                    await cur.execute("""
                        UPDATE powerbank 
                        SET status = 'written_off', write_off_reason = %s, updated_at = %s
                        WHERE id = %s
                    """, (reason, get_moscow_time(), powerbank_id))
                    
                    # Удаляем из всех станций
                    await self._remove_powerbank_from_all_stations(powerbank_id)
                    
                    return {
                        "success": True,
                        "message": f"Повербанк {powerbank_data[1]} деактивирован",
                        "powerbank_id": powerbank_id,
                        "admin_user_id": admin_user_id,
                        "deactivated_at": get_moscow_time().isoformat(),
                        "reason": reason
                    }
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка деактивации: {str(e)}"
            }
    
    async def get_powerbank_status(self, powerbank_id: int) -> Dict[str, Any]:
        """Получает статус повербанка"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT p.id, p.serial_number, p.status, p.soh, p.org_unit_id, p.created_at,
                               ou.name as org_unit_name,
                               sp.station_id, sp.slot_number, s.box_id
                        FROM powerbank p
                        LEFT JOIN org_unit ou ON p.org_unit_id = ou.org_unit_id
                        LEFT JOIN station_powerbank sp ON p.id = sp.powerbank_id
                        LEFT JOIN station s ON sp.station_id = s.station_id
                        WHERE p.id = %s
                    """, (powerbank_id,))
                    
                    result = await cur.fetchone()
                    if result:
                        return dict(result)
                    else:
                        return {"error": "Повербанк не найден"}
                        
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {"error": str(e)}
    
    async def bulk_activate_powerbanks(self, powerbank_ids: List[int], admin_user_id: int, target_org_unit_id: int = None) -> Dict[str, Any]:
        """Массовая активация повербанков"""
        try:
            results = []
            success_count = 0
            error_count = 0
            
            for powerbank_id in powerbank_ids:
                result = await self.activate_powerbank(powerbank_id, admin_user_id, target_org_unit_id)
                results.append(result)
                
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1
            
            return {
                "success": True,
                "message": f"Обработано {len(powerbank_ids)} повербанков",
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка массовой активации: {str(e)}"
            }
    
    async def _sync_activated_powerbank_to_stations(self, powerbank_id: int) -> None:
        """Синхронизирует активированный повербанк со станциями"""
        try:
            # Получаем информацию о повербанке
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT p.serial_number, p.org_unit_id 
                        FROM powerbank p WHERE p.id = %s
                    """, (powerbank_id,))
                    
                    result = await cur.fetchone()
                    if not result:
                        return
                    
                    serial_number, org_unit_id = result
                    
                    # Находим станции в той же группе
                    await cur.execute("""
                        SELECT s.station_id 
                        FROM station s 
                        WHERE s.org_unit_id = %s AND s.status = 'active'
                    """, (org_unit_id,))
                    
                    stations = await cur.fetchall()
                    
                    # Проверяем, есть ли повербанк в какой-либо станции
                    await cur.execute("""
                        SELECT sp.station_id, sp.slot_number 
                        FROM station_powerbank sp 
                        WHERE sp.powerbank_id = %s
                    """, (powerbank_id,))
                    
                    existing = await cur.fetchone()
                    if existing:
                        print(f"Повербанк {serial_number} уже находится в станции {existing[0]}, слот {existing[1]}")
                    else:
                        print(f"Повербанк {serial_number} активирован и готов к использованию в группе {org_unit_id}")
                        
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def _remove_powerbank_from_all_stations(self, powerbank_id: int) -> None:
        """Удаляет повербанк из всех станций"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Удаляем из всех станций
                    await cur.execute("""
                        DELETE FROM station_powerbank WHERE powerbank_id = %s
                    """, (powerbank_id,))
                    
                    # Обновляем счетчики станций
                    await cur.execute("""
                        UPDATE station s 
                        SET remain_num = (
                            SELECT COUNT(*) 
                            FROM station_powerbank sp
                            JOIN powerbank p ON sp.powerbank_id = p.id
                            WHERE sp.station_id = s.station_id 
                            AND p.status = 'active'
                        )
                    """)
                    
                    print(f"Повербанк {powerbank_id} удален из всех станций")
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
    
    async def get_powerbank_statistics(self) -> Dict[str, Any]:
        """Получает статистику по повербанкам"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Общая статистика
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                            SUM(CASE WHEN status = 'unknown' THEN 1 ELSE 0 END) as unknown,
                            SUM(CASE WHEN status = 'user_reported_broken' THEN 1 ELSE 0 END) as broken,
                            SUM(CASE WHEN status = 'system_error' THEN 1 ELSE 0 END) as system_error,
                            SUM(CASE WHEN status = 'written_off' THEN 1 ELSE 0 END) as written_off
                        FROM powerbank
                    """)
                    
                    stats = await cur.fetchone()
                    
                    # Статистика по группам
                    await cur.execute("""
                        SELECT ou.name as org_unit_name, COUNT(*) as count
                        FROM powerbank p
                        JOIN org_unit ou ON p.org_unit_id = ou.org_unit_id
                        WHERE p.status = 'unknown'
                        GROUP BY ou.org_unit_id, ou.name
                        ORDER BY count DESC
                    """)
                    
                    group_stats = await cur.fetchall()
                    
                    return {
                        "total": stats[0],
                        "active": stats[1],
                        "unknown": stats[2],
                        "broken": stats[3],
                        "system_error": stats[4],
                        "written_off": stats[5],
                        "group_statistics": [{"org_unit_name": row[0], "count": row[1]} for row in group_stats]
                    }
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {"error": str(e)}
    
    async def force_eject_powerbank(self, station_id: int, slot_number: int, admin_user_id: int) -> Dict[str, Any]:
        """Принудительное извлечение повербанка из указанного слота станции"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Проверяем, что станция существует
                    await cur.execute("""
                        SELECT station_id, box_id, status FROM station WHERE station_id = %s
                    """, (station_id,))
                    
                    station_data = await cur.fetchone()
                    if not station_data:
                        return {
                            "success": False,
                            "message": "Станция не найдена"
                        }
                    
                    # Проверяем, что станция активна
                    if station_data[2] != 'active':
                        return {
                            "success": False,
                            "message": "Станция неактивна"
                        }
                    
                    # Проверяем, что станция была онлайн в течение последних 30 секунд
                    from utils.station_utils import validate_station_for_operation
                    station_valid, station_message = await validate_station_for_operation(
                        self.db_pool, self.connection_manager, station_id, "принудительное извлечение powerbank'а", 30
                    )
                    
                    if not station_valid:
                        return {
                            "success": False,
                            "message": station_message
                        }
                    
                    # Проверяем, есть ли повербанк в указанном слоте
                    await cur.execute("""
                        SELECT sp.powerbank_id, p.serial_number, sp.level, sp.voltage, sp.temperature
                        FROM station_powerbank sp
                        JOIN powerbank p ON sp.powerbank_id = p.id
                        WHERE sp.station_id = %s AND sp.slot_number = %s
                    """, (station_id, slot_number))
                    
                    powerbank_data = await cur.fetchone()
                    if not powerbank_data:
                        return {
                            "success": False,
                            "message": f"В слоте {slot_number} станции {station_id} нет повербанка"
                        }
                    
                    powerbank_id, serial_number, level, voltage, temperature = powerbank_data
                    
                    # Удаляем повербанк из станции
                    await cur.execute("""
                        DELETE FROM station_powerbank 
                        WHERE station_id = %s AND slot_number = %s
                    """, (station_id, slot_number))
                    
                    # Обновляем счетчик станции
                    await cur.execute("""
                        UPDATE station 
                        SET remain_num = (
                            SELECT COUNT(*) 
                            FROM station_powerbank sp
                            JOIN powerbank p ON sp.powerbank_id = p.id
                            WHERE sp.station_id = %s AND p.status = 'active'
                        )
                        WHERE station_id = %s
                    """, (station_id, station_id))
                    
                    # Проверяем существование пользователя или создаем системного пользователя
                    await cur.execute("""
                        SELECT user_id FROM app_user WHERE user_id = %s
                    """, (admin_user_id,))
                    user_exists = await cur.fetchone()
                    
                    if not user_exists:
                        # Создаем системного пользователя для административных операций
                        await cur.execute("""
                            INSERT INTO app_user (user_id, username, email, phone, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE username = VALUES(username)
                        """, (admin_user_id, f'admin_user_{admin_user_id}', f'admin_{admin_user_id}@system.local', '0000000000', 'active', get_moscow_time()))
                    
                    # Создаем запись о принудительном извлечении
                    # Не создаем заказ для принудительного извлечения
                    # Это просто команда станции, не заказ пользователя
                    
                    # Отправляем команду принудительного извлечения станции
                    if self.connection_manager:
                        try:
                            connection = self.connection_manager.get_connection_by_station_id(station_id)
                            if connection and connection.writer and not connection.writer.is_closing():
                                from utils.packet_utils import build_force_eject_request
                                force_eject_command = build_force_eject_request(
                                    secret_key=connection.secret_key,
                                    slot=slot_number,
                                    vsn=1
                                )
                                
                                # Логируем исходящий пакет
                                station_info = {
                                    "station_id": station_id,
                                    "box_id": connection.box_id,
                                    "slot_number": slot_number,
                                    "powerbank_id": powerbank_id,
                                    "serial_number": serial_number,
                                    "admin_user_id": admin_user_id
                                }
                                
                                
                                connection.writer.write(force_eject_command)
                                await connection.writer.drain()
                                print(f"Команда принудительного извлечения отправлена станции {station_id}, слот {slot_number}")
                            else:
                                print(f"TCP соединение со станцией {station_id} недоступно")
                        except Exception as e:
                            self.logger.error(f"Ошибка: {e}")
                    
                    return {
                        "success": True,
                        "message": f"Повербанк {serial_number} принудительно извлечен из слота {slot_number}",
                        "station_id": station_id,
                        "slot_number": slot_number,
                        "powerbank_id": powerbank_id,
                        "serial_number": serial_number,
                        "admin_user_id": admin_user_id,
                        "ejected_at": get_moscow_time().isoformat(),
                        "powerbank_data": {
                            "level": level,
                            "voltage": voltage,
                            "temperature": temperature
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка извлечения: {str(e)}"
            }
