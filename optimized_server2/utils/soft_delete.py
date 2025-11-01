"""
Утилиты для поддержки мягкого удаления 
"""
from datetime import datetime
import aiomysql


class SoftDeleteMixin:
    """Миксин для добавления поддержки мягкого удаления в CRUD операции"""
    
    @staticmethod
    async def soft_delete(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Мягкое удаление записи из таблицы
        
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    query = f"""
                        UPDATE `{table}` 
                        SET is_deleted = 1, deleted_at = %s 
                        WHERE {id_field} = %s AND is_deleted = 0
                    """
                    await cur.execute(query, (datetime.now(), record_id))
                    await conn.commit()
                    
                    affected_rows = cur.rowcount
                    if affected_rows > 0:
                        return True
                    else:
                        return False
                        
        except Exception as e:
            return False
    
    @staticmethod
    async def restore(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Восстановление мягко удаленной записи
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    query = f"""
                        UPDATE `{table}` 
                        SET is_deleted = 0, deleted_at = NULL 
                        WHERE {id_field} = %s AND is_deleted = 1
                    """
                    await cur.execute(query, (record_id,))
                    await conn.commit()
                    
                    affected_rows = cur.rowcount
                    if affected_rows > 0:
                        return True
                    else:
                        return False
                        
        except Exception as e:
            return False
    
    @staticmethod
    async def hard_delete(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Физическое удаление записи из таблицы 
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Для powerbank проверяем существование и статус
                    if table == 'powerbank':
                        # Сначала проверяем, существует ли повербанк вообще
                        await cur.execute(
                            f"SELECT id, power_er, status FROM `{table}` WHERE {id_field} = %s",
                            (record_id,)
                        )
                        powerbank = await cur.fetchone()
                        if not powerbank:
                            return False
                        
                        power_er = powerbank[1] if len(powerbank) > 1 else None
                        status = powerbank[2] if len(powerbank) > 2 else None
                    
                    # Для станций сначала удаляем связанные записи
                    if table == 'station':
                        # Удаляем секретный ключ станции
                        await cur.execute(
                            "DELETE FROM `station_secret_key` WHERE station_id = %s",
                            (record_id,)
                        )
                        
                        # Удаляем связи станции с повербанками
                        await cur.execute(
                            "DELETE FROM `station_powerbank` WHERE station_id = %s",
                            (record_id,)
                        )
                    
                    # Удаляем основную запись
                    query = f"DELETE FROM `{table}` WHERE {id_field} = %s"
                    await cur.execute(query, (record_id,))
                    await conn.commit()
                    
                    affected_rows = cur.rowcount
                    if affected_rows > 0:
                        return True
                    else:
                        return False
                        
        except Exception as e:
            return False
    
    @staticmethod
    async def get_deleted_records(db_pool, table: str, limit: int = 100, offset: int = 0) -> list:
        """
        Получает список удаленных записей
       
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    query = f"""
                        SELECT * FROM `{table}` 
                        WHERE is_deleted = 1 
                        ORDER BY deleted_at DESC 
                        LIMIT %s OFFSET %s
                    """
                    await cur.execute(query, (limit, offset))
                    records = await cur.fetchall()
                    return records
                    
        except Exception as e:
            return []
    
    @staticmethod
    async def count_deleted_records(db_pool, table: str) -> int:
        """
        Подсчитывает количество удаленных записей
       
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Для powerbank используем power_er = 5, для остальных - is_deleted = 1
                    if table == 'powerbank':
                        query = f"SELECT COUNT(*) FROM `{table}` WHERE power_er = 5 AND status = 'system_error'"
                    else:
                        query = f"SELECT COUNT(*) FROM `{table}` WHERE is_deleted = 1"
                    await cur.execute(query)
                    result = await cur.fetchone()
                    return result[0] if result else 0
                    
        except Exception as e:
            return 0
    
    @staticmethod
    def add_not_deleted_filter(where_clause: str = "") -> str:
        """
        Добавляет фильтр для исключения удаленных записей в WHERE условие
        
        """
        if where_clause:
            return f"{where_clause} AND is_deleted = 0"
        else:
            return "is_deleted = 0"


# Функции-хелперы для удобного использования
async def soft_delete_user(db_pool, user_id: int) -> bool:
    """
    Мягкое удаление пользователя
   
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `app_user` 
                    SET is_deleted = 1, deleted_at = %s, status = 'blocked'
                    WHERE user_id = %s AND is_deleted = 0
                """
                await cur.execute(query, (datetime.now(), user_id))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def soft_delete_station(db_pool, station_id: int) -> bool:
    """
    Мягкое удаление станции
   
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `station` 
                    SET is_deleted = 1, deleted_at = %s, status = 'inactive'
                    WHERE station_id = %s AND is_deleted = 0
                """
                await cur.execute(query, (datetime.now(), station_id))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def soft_delete_powerbank(db_pool, powerbank_id: int) -> bool:
    """
    Мягкое удаление повербанка
    
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Сначала проверяем существование повербанка
                await cur.execute("SELECT id, power_er, status FROM `powerbank` WHERE id = %s", (powerbank_id,))
                powerbank = await cur.fetchone()
                
                if not powerbank:
                    return False
                
                # Если уже удален - возвращаем True (уже помечен как удаленный)
                power_er = powerbank[1] if len(powerbank) > 1 else None
                status = powerbank[2] if len(powerbank) > 2 else None
                if power_er == 5 and status == 'system_error':
                    return True
                
                query = """
                    UPDATE `powerbank` 
                    SET power_er = 5, status = 'system_error', deleted_at = %s
                    WHERE id = %s
                """
                await cur.execute(query, (datetime.now(), powerbank_id))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def soft_delete_org_unit(db_pool, org_unit_id: int) -> bool:
    """Мягкое удаление организационной единицы"""
    return await SoftDeleteMixin.soft_delete(db_pool, 'org_unit', org_unit_id, 'org_unit_id')


async def soft_delete_order(db_pool, order_id: int) -> bool:
    """Мягкое удаление заказа"""
    return await SoftDeleteMixin.soft_delete(db_pool, 'orders', order_id, 'id')


async def restore_user(db_pool, user_id: int) -> bool:
    """
    Восстановление пользователя
    При восстановлении также меняет статус на 'active'
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `app_user` 
                    SET is_deleted = 0, deleted_at = NULL, status = 'active'
                    WHERE user_id = %s AND is_deleted = 1
                """
                await cur.execute(query, (user_id,))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def restore_station(db_pool, station_id: int) -> bool:
    """
    Восстановление станции
    При восстановлении также меняет статус на 'active'
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `station` 
                    SET is_deleted = 0, deleted_at = NULL, status = 'active'
                    WHERE station_id = %s AND is_deleted = 1
                """
                await cur.execute(query, (station_id,))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def restore_powerbank(db_pool, powerbank_id: int) -> bool:
    """
    Восстановление повербанка
    При восстановлении сбрасывает power_er и меняет статус на 'active'
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `powerbank` 
                    SET power_er = NULL, deleted_at = NULL, status = 'active'
                    WHERE id = %s AND power_er = 5 AND status = 'system_error'
                """
                await cur.execute(query, (powerbank_id,))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    return True
                else:
                    return False
                    
    except Exception as e:
        return False


async def restore_org_unit(db_pool, org_unit_id: int) -> bool:
    """Восстановление организационной единицы"""
    return await SoftDeleteMixin.restore(db_pool, 'org_unit', org_unit_id, 'org_unit_id')


async def restore_order(db_pool, order_id: int) -> bool:
    """Восстановление заказа"""
    return await SoftDeleteMixin.restore(db_pool, 'orders', order_id, 'id')


async def get_deleted_users(db_pool, limit: int = 100, offset: int = 0) -> list:
    """Получить список удаленных пользователей"""
    return await SoftDeleteMixin.get_deleted_records(db_pool, 'app_user', limit, offset)


async def get_deleted_stations(db_pool, limit: int = 100, offset: int = 0) -> list:
    """Получить список удаленных станций"""
    return await SoftDeleteMixin.get_deleted_records(db_pool, 'station', limit, offset)


async def get_deleted_powerbanks(db_pool, limit: int = 100, offset: int = 0) -> list:
    """Получить список удаленных повербанков (power_er = 5)"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                query = """
                    SELECT * FROM `powerbank` 
                    WHERE power_er = 5 AND status = 'system_error'
                    ORDER BY deleted_at DESC 
                    LIMIT %s OFFSET %s
                """
                await cur.execute(query, (limit, offset))
                records = await cur.fetchall()
                return records
                
    except Exception as e:
        return []

