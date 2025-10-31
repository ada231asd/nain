"""
API для жесткого удаления (физическое удаление из БД)
ВНИМАНИЕ: Операции необратимы!
"""
from aiohttp import web
from aiohttp.web import Request, Response
import aiomysql
from datetime import datetime, timedelta
from utils.soft_delete import SoftDeleteMixin
from utils.centralized_logger import get_logger


logger = get_logger('hard_delete_api')


class HardDeleteAPI:
    """API для физического удаления записей из БД"""
    
    def __init__(self, db_pool, connection_manager=None):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def hard_delete_entity(self, request: Request) -> Response:
        """DELETE /api/hard-delete/{entity_type}/{entity_id} - Физическое удаление записи"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({'error': 'Требуется авторизация'}, status=401)
            
            # Проверка прав service_admin
            if not await self._check_service_admin(user['user_id']):
                return web.json_response({'error': 'Недостаточно прав для жесткого удаления'}, status=403)
            
            entity_type = request.match_info['entity_type']
            entity_id = int(request.match_info['entity_id'])
            
            # Проверка подтверждения
            try:
                data = await request.json()
                if not data.get('confirm'):
                    return web.json_response({'error': 'Необходимо подтверждение (confirm: true)'}, status=400)
            except:
                return web.json_response({'error': 'Необходимо подтверждение (confirm: true)'}, status=400)
            
            # Маппинг типов на таблицы и ID поля
            table_mapping = {
                'user': ('app_user', 'user_id'),
                'station': ('station', 'station_id'),
                'powerbank': ('powerbank', 'id'),
                'org_unit': ('org_unit', 'org_unit_id'),
                'order': ('orders', 'id')
            }
            
            if entity_type not in table_mapping:
                return web.json_response({'error': f'Неподдерживаемый тип: {entity_type}'}, status=400)
            
            table, id_field = table_mapping[entity_type]
            
            # Для повербанков находим станцию до удаления
            station_id = None
            if entity_type == 'powerbank' and self.connection_manager:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(
                            "SELECT station_id FROM station_powerbank WHERE powerbank_id = %s LIMIT 1",
                            (entity_id,)
                        )
                        result = await cur.fetchone()
                        if result:
                            station_id = result['station_id']
            
            # Физическое удаление
            success = await SoftDeleteMixin.hard_delete(self.db_pool, table, entity_id, id_field)
            
            if success:
                # Для повербанков отправляем запрос инвентаризации на станцию
                if entity_type == 'powerbank' and station_id and self.connection_manager:
                    try:
                        from handlers.query_inventory import QueryInventoryHandler
                        inventory_handler = QueryInventoryHandler(self.db_pool, self.connection_manager)
                        await inventory_handler.send_inventory_request(station_id)
                        logger.info(f"Отправлен запрос инвентаризации на станцию {station_id} после жесткого удаления повербанка {entity_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось отправить запрос инвентаризации для станции {station_id} после жесткого удаления повербанка {entity_id}: {e}")
                
                logger.warning(f"ЖЕСТКОЕ УДАЛЕНИЕ: {entity_type} #{entity_id} by user {user['user_id']}")
                return web.json_response({
                    'success': True,
                    'message': f'{entity_type} #{entity_id} физически удален из базы данных'
                })
            else:
                return web.json_response({'error': f'{entity_type} #{entity_id} не найден'}, status=404)
            
        except ValueError:
            return web.json_response({'error': 'Некорректный ID'}, status=400)
        except Exception as e:
            logger.error(f"Ошибка при жестком удалении: {e}", exc_info=True)
            return web.json_response({'error': f'Ошибка при удалении: {str(e)}'}, status=500)
    
    async def cleanup_old_deleted(self, request: Request) -> Response:
        """DELETE /api/hard-delete/cleanup - Удалить старые записи с is_deleted = 1"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({'error': 'Требуется авторизация'}, status=401)
            
            # Проверка прав service_admin
            if not await self._check_service_admin(user['user_id']):
                return web.json_response({'error': 'Недостаточно прав для очистки'}, status=403)
            
            # Получение параметров
            data = await request.json()
            entity_type = data.get('entity_type')
            days_old = data.get('days_old', 90)  # По умолчанию 90 дней
            
            if not entity_type:
                return web.json_response({'error': 'Необходимо указать entity_type'}, status=400)
            
            # Маппинг типов на таблицы
            table_mapping = {
                'user': 'app_user',
                'station': 'station',
                'powerbank': 'powerbank',
                'org_unit': 'org_unit',
                'order': 'orders',
                'user_role': 'user_role',
                'user_favorites': 'user_favorites'
            }
            
            if entity_type not in table_mapping:
                return web.json_response({'error': f'Неподдерживаемый тип: {entity_type}'}, status=400)
            
            table = table_mapping[entity_type]
            
            # Вычисляем дату отсечки
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Удаляем старые записи
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Для powerbank используем power_er = 5, для остальных - только по deleted_at
                    if table == 'powerbank':
                        query = f"""
                            DELETE FROM `{table}` 
                            WHERE power_er = 5 AND status = 'system_error'
                            AND deleted_at < %s
                        """
                    else:
                        query = f"""
                            DELETE FROM `{table}` 
                            WHERE deleted_at < %s
                        """
                    await cur.execute(query, (cutoff_date,))
                    await conn.commit()
                    
                    deleted_count = cur.rowcount
            
            logger.warning(f"ОЧИСТКА: Удалено {deleted_count} записей {entity_type} старше {days_old} дней by user {user['user_id']}")
            
            return web.json_response({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Удалено {deleted_count} записей {entity_type} старше {days_old} дней'
            })
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых записей: {e}", exc_info=True)
            return web.json_response({'error': f'Ошибка при очистке: {str(e)}'}, status=500)
    
    async def get_cleanup_candidates(self, request: Request) -> Response:
        """GET /api/hard-delete/cleanup/preview - Список записей для очистки"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({'error': 'Требуется авторизация'}, status=401)
            
            # Проверка прав service_admin
            if not await self._check_service_admin(user['user_id']):
                return web.json_response({'error': 'Недостаточно прав'}, status=403)
            
            # Параметры
            entity_type = request.query.get('entity_type')
            days_old = int(request.query.get('days_old', 90))
            
            if not entity_type:
                return web.json_response({'error': 'Необходимо указать entity_type'}, status=400)
            
            # Маппинг типов на таблицы
            table_mapping = {
                'user': 'app_user',
                'station': 'station',
                'powerbank': 'powerbank',
                'org_unit': 'org_unit',
                'order': 'orders'
            }
            
            if entity_type not in table_mapping:
                return web.json_response({'error': f'Неподдерживаемый тип: {entity_type}'}, status=400)
            
            table = table_mapping[entity_type]
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Получаем кандидатов на удаление
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Для powerbank используем power_er = 5, для остальных - только по deleted_at
                    if table == 'powerbank':
                        query = f"""
                            SELECT * FROM `{table}` 
                            WHERE power_er = 5 AND status = 'system_error'
                            AND deleted_at < %s
                            LIMIT 100
                        """
                        count_query = f"""
                            SELECT COUNT(*) as count FROM `{table}` 
                            WHERE power_er = 5 AND status = 'system_error'
                            AND deleted_at < %s
                        """
                    else:
                        query = f"""
                            SELECT * FROM `{table}` 
                            WHERE deleted_at < %s
                            LIMIT 100
                        """
                        count_query = f"""
                            SELECT COUNT(*) as count FROM `{table}` 
                            WHERE deleted_at < %s
                        """
                    await cur.execute(query, (cutoff_date,))
                    candidates = await cur.fetchall()
                    
                    # Подсчитываем общее количество
                    await cur.execute(count_query, (cutoff_date,))
                    total = (await cur.fetchone())['count']
            
            return web.json_response({
                'success': True,
                'entity_type': entity_type,
                'days_old': days_old,
                'total_candidates': total,
                'preview': candidates[:10],  # Показываем первые 10
                'message': f'Найдено {total} записей для удаления'
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении кандидатов: {e}", exc_info=True)
            return web.json_response({'error': f'Ошибка: {str(e)}'}, status=500)
    
    async def _check_service_admin(self, user_id: int) -> bool:
        """Проверка прав service_admin"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT role FROM user_role 
                    WHERE user_id = %s AND role = 'service_admin'
                """, (user_id,))
                return await cur.fetchone() is not None

