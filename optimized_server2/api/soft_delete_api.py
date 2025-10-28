"""
API для управления мягким удалением (soft delete)
Позволяет администраторам удалять, восстанавливать и просматривать удаленные записи
"""
from aiohttp import web
from aiohttp.web import Request, Response
import aiomysql
from utils.soft_delete import (
    soft_delete_user, soft_delete_station, soft_delete_powerbank, 
    soft_delete_org_unit, soft_delete_order,
    restore_user, restore_station, restore_powerbank, 
    restore_org_unit, restore_order,
    get_deleted_users, get_deleted_stations, get_deleted_powerbanks,
    SoftDeleteMixin
)
from utils.centralized_logger import get_logger


logger = get_logger('soft_delete_api')


class SoftDeleteAPI:
    """API для управления мягким удалением"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def soft_delete_entity(self, request: Request) -> Response:
        """DELETE /api/soft-delete/{entity_type}/{entity_id} - Мягкое удаление"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверка прав администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для удаления'
                }, status=403)
            
            entity_type = request.match_info['entity_type']
            entity_id = int(request.match_info['entity_id'])
            
            # Выполняем мягкое удаление в зависимости от типа сущности
            delete_functions = {
                'user': soft_delete_user,
                'station': soft_delete_station,
                'powerbank': soft_delete_powerbank,
                'org_unit': soft_delete_org_unit,
                'order': soft_delete_order
            }
            
            if entity_type not in delete_functions:
                return web.json_response({
                    'error': f'Неподдерживаемый тип сущности: {entity_type}'
                }, status=400)
            
            success = await delete_functions[entity_type](self.db_pool, entity_id)
            
            if success:
                logger.info(f"Пользователь {user['user_id']} удалил {entity_type} #{entity_id}")
                return web.json_response({
                    'success': True,
                    'message': f'{entity_type} #{entity_id} успешно удален'
                })
            else:
                return web.json_response({
                    'error': f'{entity_type} #{entity_id} не найден или уже удален'
                }, status=404)
            
        except ValueError:
            return web.json_response({
                'error': 'Некорректный ID'
            }, status=400)
        except Exception as e:
            logger.error(f"Ошибка при мягком удалении: {e}", exc_info=True)
            return web.json_response({
                'error': f'Ошибка при удалении: {str(e)}'
            }, status=500)
    
    async def restore_entity(self, request: Request) -> Response:
        """POST /api/soft-delete/restore/{entity_type}/{entity_id} - Восстановление"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверка прав администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для восстановления'
                }, status=403)
            
            entity_type = request.match_info['entity_type']
            entity_id = int(request.match_info['entity_id'])
            
            # Выполняем восстановление в зависимости от типа сущности
            restore_functions = {
                'user': restore_user,
                'station': restore_station,
                'powerbank': restore_powerbank,
                'org_unit': restore_org_unit,
                'order': restore_order
            }
            
            if entity_type not in restore_functions:
                return web.json_response({
                    'error': f'Неподдерживаемый тип сущности: {entity_type}'
                }, status=400)
            
            success = await restore_functions[entity_type](self.db_pool, entity_id)
            
            if success:
                logger.info(f"Пользователь {user['user_id']} восстановил {entity_type} #{entity_id}")
                return web.json_response({
                    'success': True,
                    'message': f'{entity_type} #{entity_id} успешно восстановлен'
                })
            else:
                return web.json_response({
                    'error': f'{entity_type} #{entity_id} не найден или не был удален'
                }, status=404)
            
        except ValueError:
            return web.json_response({
                'error': 'Некорректный ID'
            }, status=400)
        except Exception as e:
            logger.error(f"Ошибка при восстановлении: {e}", exc_info=True)
            return web.json_response({
                'error': f'Ошибка при восстановлении: {str(e)}'
            }, status=500)
    
    async def get_deleted_entities(self, request: Request) -> Response:
        """GET /api/soft-delete/{entity_type} - Получить список удаленных"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверка прав администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для просмотра удаленных записей'
                }, status=403)
            
            entity_type = request.match_info['entity_type']
            
            # Параметры пагинации
            limit = int(request.query.get('limit', 50))
            offset = int(request.query.get('offset', 0))
            
            # Получаем удаленные записи
            get_functions = {
                'user': get_deleted_users,
                'station': get_deleted_stations,
                'powerbank': get_deleted_powerbanks
            }
            
            if entity_type not in get_functions:
                return web.json_response({
                    'error': f'Неподдерживаемый тип сущности: {entity_type}'
                }, status=400)
            
            records = await get_functions[entity_type](self.db_pool, limit, offset)
            total = await SoftDeleteMixin.count_deleted_records(
                self.db_pool, 
                {'user': 'app_user', 'station': 'station', 'powerbank': 'powerbank'}[entity_type]
            )
            
            return web.json_response({
                'success': True,
                'entity_type': entity_type,
                'records': records,
                'total': total,
                'limit': limit,
                'offset': offset
            })
            
        except ValueError:
            return web.json_response({
                'error': 'Некорректные параметры пагинации'
            }, status=400)
        except Exception as e:
            logger.error(f"Ошибка при получении удаленных записей: {e}", exc_info=True)
            return web.json_response({
                'error': f'Ошибка при получении записей: {str(e)}'
            }, status=500)
    
    async def get_statistics(self, request: Request) -> Response:
        """GET /api/soft-delete/statistics - Статистика по удаленным записям"""
        try:
            # Проверка авторизации
            user = request.get('user')
            if not user:
                return web.json_response({
                    'error': 'Требуется авторизация'
                }, status=401)
            
            # Проверка прав администратора
            if not await self._check_admin_permissions(user['user_id']):
                return web.json_response({
                    'error': 'Недостаточно прав для просмотра статистики'
                }, status=403)
            
            # Подсчитываем удаленные записи по всем таблицам
            stats = {
                'users': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'app_user'),
                'stations': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'station'),
                'powerbanks': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'powerbank'),
                'org_units': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'org_unit'),
                'orders': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'orders'),
                'user_roles': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'user_role'),
                'user_favorites': await SoftDeleteMixin.count_deleted_records(self.db_pool, 'user_favorites')
            }
            
            stats['total'] = sum(stats.values())
            
            return web.json_response({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
            return web.json_response({
                'error': f'Ошибка при получении статистики: {str(e)}'
            }, status=500)
    
    async def _check_admin_permissions(self, user_id: int) -> bool:
        """Проверяет права администратора"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Проверяем есть ли у таблицы user_role колонка is_deleted
                await cur.execute("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'user_role' 
                    AND COLUMN_NAME = 'is_deleted'
                    AND TABLE_SCHEMA = DATABASE()
                """)
                has_is_deleted = (await cur.fetchone())[0] > 0
                
                # Если колонка is_deleted есть, используем её в фильтре
                if has_is_deleted:
                    await cur.execute("""
                        SELECT role FROM user_role 
                        WHERE user_id = %s 
                        AND role IN ('service_admin', 'group_admin', 'subgroup_admin')
                        AND is_deleted = 0
                    """, (user_id,))
                else:
                    # Иначе проверяем без фильтра is_deleted
                    await cur.execute("""
                        SELECT role FROM user_role 
                        WHERE user_id = %s 
                        AND role IN ('service_admin', 'group_admin', 'subgroup_admin')
                    """, (user_id,))
                
                roles = await cur.fetchall()
                return len(roles) > 0

