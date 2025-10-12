"""
Модель для работы с представлением v_powerbank_status
"""
import aiomysql
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from utils.centralized_logger import get_logger


class PowerbankStatus:
    """Модель для работы со статусами повербанков"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_powerbanks_with_status(
        self, 
        status_filter: Optional[str] = None,
        org_unit_id: Optional[int] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Получить повербанки с их статусами
        
        Args:
            status_filter: Фильтр по статусу ('in_station', 'in_use', 'not_returned')
            org_unit_id: Фильтр по группе
            page: Номер страницы
            limit: Количество записей на странице
            
        Returns:
            Tuple[List[Dict], int]: (список повербанков, общее количество)
        """
        try:
            logger = get_logger('powerbank_status')
            
            # Базовый запрос с дополнительной информацией
            base_query = """
                SELECT 
                    vps.powerbank_id,
                    vps.serial_number,
                    vps.status,
                    vps.station_id,
                    vps.user_id,
                    vps.borrow_time,
                    vps.completed_at,
                    s.box_id as station_name,
                    au.fio as user_name,
                    au.phone_e164 as user_phone,
                    au.email as user_email,
                    ou.name as org_unit_name
                FROM v_powerbank_status vps
                LEFT JOIN station s ON s.station_id = vps.station_id
                LEFT JOIN app_user au ON au.user_id = vps.user_id
                LEFT JOIN powerbank pb ON pb.id = vps.powerbank_id
                LEFT JOIN org_unit ou ON ou.org_unit_id = pb.org_unit_id
                WHERE 1=1
            """
            
            count_query = """
                SELECT COUNT(*) as total
                FROM v_powerbank_status vps
                LEFT JOIN powerbank pb ON pb.id = vps.powerbank_id
                WHERE 1=1
            """
            
            # Создаем отдельные списки параметров для count и base запросов
            count_params = []
            base_params = []
            
            # Добавляем фильтры
            if status_filter:
                base_query += " AND vps.status = %s"
                count_query += " AND vps.status = %s"
                count_params.append(status_filter)
                base_params.append(status_filter)
            
            if org_unit_id:
                base_query += " AND pb.org_unit_id = %s"
                count_query += " AND pb.org_unit_id = %s"
                count_params.append(org_unit_id)
                base_params.append(org_unit_id)
            
            # Добавляем сортировку и пагинацию только к base_query
            base_query += " ORDER BY vps.powerbank_id DESC"
            base_query += " LIMIT %s OFFSET %s"
            base_params.extend([limit, (page - 1) * limit])
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Получаем общее количество
                    await cur.execute(count_query, count_params)
                    total_result = await cur.fetchone()
                    total = total_result['total'] if total_result else 0
                    
                    # Получаем данные
                    await cur.execute(base_query, base_params)
                    powerbanks = await cur.fetchall()
                    
                    logger.info(f"Получено {len(powerbanks)} повербанков из {total} (фильтр: {status_filter}, группа: {org_unit_id})")
                    
                    return powerbanks, total
                    
        except Exception as e:
            logger = get_logger('powerbank_status')
            logger.error(f"Ошибка получения повербанков со статусами: {e}")
            raise e
    
    async def get_powerbank_status_summary(self, org_unit_id: Optional[int] = None) -> Dict[str, int]:
        """
        Получить сводку по статусам повербанков
        
        Args:
            org_unit_id: Фильтр по группе
            
        Returns:
            Dict[str, int]: Словарь со счетчиками по статусам
        """
        try:
            logger = get_logger('powerbank_status')
            
            if org_unit_id:
                query = """
                    SELECT 
                        vps.status,
                        COUNT(*) as count
                    FROM v_powerbank_status vps
                    LEFT JOIN powerbank pb ON pb.id = vps.powerbank_id
                    WHERE pb.org_unit_id = %s
                    GROUP BY vps.status
                """
                params = [org_unit_id]
            else:
                query = """
                    SELECT 
                        vps.status,
                        COUNT(*) as count
                    FROM v_powerbank_status vps
                    GROUP BY vps.status
                """
                params = []
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    results = await cur.fetchall()
                    
                    summary = {
                        'in_station': 0,
                        'in_use': 0,
                        'not_returned': 0
                    }
                    
                    for row in results:
                        summary[row['status']] = row['count']
                    
                    logger.info(f"Сводка по статусам: {summary}")
                    return summary
                    
        except Exception as e:
            logger = get_logger('powerbank_status')
            logger.error(f"Ошибка получения сводки по статусам: {e}")
            raise e
    
    async def get_powerbank_by_id(self, powerbank_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить конкретный повербанк со статусом
        
        Args:
            powerbank_id: ID повербанка
            
        Returns:
            Optional[Dict]: Данные повербанка или None
        """
        try:
            logger = get_logger('powerbank_status')
            
            query = """
                SELECT 
                    vps.powerbank_id,
                    vps.serial_number,
                    vps.status,
                    vps.station_id,
                    vps.user_id,
                    vps.borrow_time,
                    vps.completed_at,
                    s.box_id as station_name,
                    au.fio as user_name,
                    au.phone_e164 as user_phone,
                    au.email as user_email,
                    ou.name as org_unit_name
                FROM v_powerbank_status vps
                LEFT JOIN station s ON s.station_id = vps.station_id
                LEFT JOIN app_user au ON au.user_id = vps.user_id
                LEFT JOIN powerbank pb ON pb.id = vps.powerbank_id
                LEFT JOIN org_unit ou ON ou.org_unit_id = pb.org_unit_id
                WHERE vps.powerbank_id = %s
            """
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, (powerbank_id,))
                    result = await cur.fetchone()
                    
                    if result:
                        logger.info(f"Найден повербанк {powerbank_id} со статусом {result['status']}")
                    else:
                        logger.warning(f"Повербанк {powerbank_id} не найден")
                    
                    return result
                    
        except Exception as e:
            logger = get_logger('powerbank_status')
            logger.error(f"Ошибка получения повербанка {powerbank_id}: {e}")
            raise e
