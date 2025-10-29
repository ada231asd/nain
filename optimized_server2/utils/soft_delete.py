"""
Утилиты для поддержки мягкого удаления (soft delete)
Вместо физического удаления записи помечаются как удаленные
"""
from datetime import datetime
from typing import Optional, Dict, Any
import aiomysql
from utils.centralized_logger import get_logger


logger = get_logger('soft_delete')


class SoftDeleteMixin:
    """Миксин для добавления поддержки мягкого удаления в CRUD операции"""
    
    @staticmethod
    async def soft_delete(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Мягкое удаление записи из таблицы
        
        Args:
            db_pool: Пул соединений с БД
            table: Название таблицы
            record_id: ID записи для удаления
            id_field: Название поля ID (по умолчанию 'id')
            
        Returns:
            bool: True если запись успешно помечена как удаленная
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
                        logger.info(f"Запись {record_id} из таблицы {table} помечена как удаленная")
                        return True
                    else:
                        logger.warning(f"Запись {record_id} из таблицы {table} не найдена или уже удалена")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка при мягком удалении из {table}: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def restore(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Восстановление мягко удаленной записи
        
        Args:
            db_pool: Пул соединений с БД
            table: Название таблицы
            record_id: ID записи для восстановления
            id_field: Название поля ID (по умолчанию 'id')
            
        Returns:
            bool: True если запись успешно восстановлена
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
                        logger.info(f"Запись {record_id} из таблицы {table} восстановлена")
                        return True
                    else:
                        logger.warning(f"Запись {record_id} из таблицы {table} не найдена или не была удалена")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка при восстановлении записи из {table}: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def hard_delete(db_pool, table: str, record_id: int, id_field: str = 'id') -> bool:
        """
        Физическое удаление записи из таблицы (использовать с осторожностью!)
        
        Args:
            db_pool: Пул соединений с БД
            table: Название таблицы
            record_id: ID записи для удаления
            id_field: Название поля ID (по умолчанию 'id')
            
        Returns:
            bool: True если запись успешно удалена
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Для станций сначала удаляем связанные записи
                    if table == 'station':
                        # Удаляем секретный ключ станции
                        await cur.execute(
                            "DELETE FROM `station_secret_key` WHERE station_id = %s",
                            (record_id,)
                        )
                        logger.info(f"Удалены секретные ключи для станции {record_id}")
                        
                        # Удаляем связи станции с повербанками
                        await cur.execute(
                            "DELETE FROM `station_powerbank` WHERE station_id = %s",
                            (record_id,)
                        )
                        logger.info(f"Удалены связи станции {record_id} с повербанками")
                    
                    # Удаляем основную запись
                    query = f"DELETE FROM `{table}` WHERE {id_field} = %s"
                    await cur.execute(query, (record_id,))
                    await conn.commit()
                    
                    affected_rows = cur.rowcount
                    if affected_rows > 0:
                        logger.warning(f"Запись {record_id} из таблицы {table} ФИЗИЧЕСКИ УДАЛЕНА")
                        return True
                    else:
                        logger.warning(f"Запись {record_id} из таблицы {table} не найдена")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка при физическом удалении из {table}: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_deleted_records(db_pool, table: str, limit: int = 100, offset: int = 0) -> list:
        """
        Получает список удаленных записей
        
        Args:
            db_pool: Пул соединений с БД
            table: Название таблицы
            limit: Количество записей для выборки
            offset: Смещение для пагинации
            
        Returns:
            list: Список удаленных записей
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
            logger.error(f"Ошибка при получении удаленных записей из {table}: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def count_deleted_records(db_pool, table: str) -> int:
        """
        Подсчитывает количество удаленных записей
        
        Args:
            db_pool: Пул соединений с БД
            table: Название таблицы
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            async with db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    query = f"SELECT COUNT(*) FROM `{table}` WHERE is_deleted = 1"
                    await cur.execute(query)
                    result = await cur.fetchone()
                    return result[0] if result else 0
                    
        except Exception as e:
            logger.error(f"Ошибка при подсчете удаленных записей из {table}: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def add_not_deleted_filter(where_clause: str = "") -> str:
        """
        Добавляет фильтр для исключения удаленных записей в WHERE условие
        
        Args:
            where_clause: Существующее WHERE условие (без слова WHERE)
            
        Returns:
            str: WHERE условие с добавленным фильтром is_deleted = 0
        """
        if where_clause:
            return f"{where_clause} AND is_deleted = 0"
        else:
            return "is_deleted = 0"


# Функции-хелперы для удобного использования
async def soft_delete_user(db_pool, user_id: int) -> bool:
    """
    Мягкое удаление пользователя
    При удалении также меняет статус на 'blocked'
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
                    logger.info(f"Пользователь {user_id} помечен как удаленный и заблокирован")
                    return True
                else:
                    logger.warning(f"Пользователь {user_id} не найден или уже удален")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при мягком удалении пользователя {user_id}: {e}", exc_info=True)
        return False


async def soft_delete_station(db_pool, station_id: int) -> bool:
    """
    Мягкое удаление станции
    При удалении также меняет статус на 'inactive' - сервер не работает с этой станцией
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
                    logger.info(f"Станция {station_id} помечена как удаленная, статус inactive")
                    return True
                else:
                    logger.warning(f"Станция {station_id} не найдена или уже удалена")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при мягком удалении станции {station_id}: {e}", exc_info=True)
        return False


async def soft_delete_powerbank(db_pool, powerbank_id: int) -> bool:
    """
    Мягкое удаление повербанка
    При удалении также меняет статус на 'unknown'
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `powerbank` 
                    SET is_deleted = 1, deleted_at = %s, status = 'unknown'
                    WHERE id = %s AND is_deleted = 0
                """
                await cur.execute(query, (datetime.now(), powerbank_id))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    logger.info(f"Повербанк {powerbank_id} помечен как удаленный, статус unknown")
                    return True
                else:
                    logger.warning(f"Повербанк {powerbank_id} не найден или уже удален")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при мягком удалении повербанка {powerbank_id}: {e}", exc_info=True)
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
                    logger.info(f"Пользователь {user_id} восстановлен и активирован")
                    return True
                else:
                    logger.warning(f"Пользователь {user_id} не найден или не был удален")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при восстановлении пользователя {user_id}: {e}", exc_info=True)
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
                    logger.info(f"Станция {station_id} восстановлена, статус active")
                    return True
                else:
                    logger.warning(f"Станция {station_id} не найдена или не была удалена")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при восстановлении станции {station_id}: {e}", exc_info=True)
        return False


async def restore_powerbank(db_pool, powerbank_id: int) -> bool:
    """
    Восстановление повербанка
    При восстановлении также меняет статус на 'active'
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = """
                    UPDATE `powerbank` 
                    SET is_deleted = 0, deleted_at = NULL, status = 'active'
                    WHERE id = %s AND is_deleted = 1
                """
                await cur.execute(query, (powerbank_id,))
                await conn.commit()
                
                affected_rows = cur.rowcount
                if affected_rows > 0:
                    logger.info(f"Повербанк {powerbank_id} восстановлен, статус active")
                    return True
                else:
                    logger.warning(f"Повербанк {powerbank_id} не найден или не был удален")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при восстановлении повербанка {powerbank_id}: {e}", exc_info=True)
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
    """Получить список удаленных повербанков"""
    return await SoftDeleteMixin.get_deleted_records(db_pool, 'powerbank', limit, offset)

