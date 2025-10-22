"""
Утилиты для работы с организационными единицами
"""
from typing import Optional
from models.org_unit import OrgUnit
from utils.centralized_logger import get_logger
from utils.time_utils import get_moscow_time


async def is_powerbank_compatible(db_pool, powerbank_org_id: int, station_org_id: int) -> bool:
    """
    Проверяет совместимость повербанка со станцией по организационным единицам
    """
    try:
        powerbank_unit = await OrgUnit.get_by_id(db_pool, powerbank_org_id)
        station_unit = await OrgUnit.get_by_id(db_pool, station_org_id)

        if not powerbank_unit or not station_unit:
            return False

        if powerbank_unit.org_unit_id == station_unit.org_unit_id:
            return True

        if (powerbank_unit.unit_type == 'group' and 
            station_unit.parent_org_unit_id == powerbank_unit.org_unit_id):
            return True

        return False
        
    except Exception as e:
        print(f"Ошибка проверки совместимости org_unit: {e}")
        return False


async def get_compatibility_reason(db_pool, powerbank_org_id: int, station_org_id: int) -> str:
    """
    Возвращает причину совместимости/несовместимости для логирования
    
    """
    try:
        powerbank_unit = await OrgUnit.get_by_id(db_pool, powerbank_org_id)
        station_unit = await OrgUnit.get_by_id(db_pool, station_org_id)

        if not powerbank_unit:
            return f"Организационная единица повербанка {powerbank_org_id} не найдена"
        
        if not station_unit:
            return f"Организационная единица станции {station_org_id} не найдена"

        # Проверяем правила совместимости
        if powerbank_unit.org_unit_id == station_unit.org_unit_id:
            return f"Одинаковая организационная единица: {powerbank_unit.name}"

        if (powerbank_unit.unit_type == 'group' and 
            station_unit.parent_org_unit_id == powerbank_unit.org_unit_id):
            return f"Повербанк из родительской группы '{powerbank_unit.name}', станция из подгруппы '{station_unit.name}'"

        return f"Несовместимые организационные единицы: повербанк '{powerbank_unit.name}' ({powerbank_unit.unit_type}), станция '{station_unit.name}' ({station_unit.unit_type})"
        
    except Exception as e:
        return f"Ошибка определения совместимости: {e}"


async def log_powerbank_ejection_event(db_pool, station_id: int, slot_number: int, 
                                     powerbank_serial: str, powerbank_org_id: int, 
                                     station_org_id: int, reason: str) -> None:
    """
    Логирует событие выплева повербанка в файл
    
    """
    try:
        # Логируем в файл через централизованный логгер
        logger = get_logger('powerbank_ejection')
        
        # Детальное логирование события выплева
        logger.info(f"ВЫБРОС ПОВЕРБАНКА: станция {station_id}, слот {slot_number}, "
                   f"повербанк {powerbank_serial} (org_unit: {powerbank_org_id}), "
                   f"станция org_unit: {station_org_id}, причина: {reason}")
        
        # Дополнительно логируем в отдельный файл для выплевов
        ejection_logger = get_logger('powerbank_ejections')
        ejection_logger.info(f"EJECTION|{get_moscow_time().isoformat()}|"
                           f"STATION:{station_id}|SLOT:{slot_number}|"
                           f"POWERBANK:{powerbank_serial}|"
                           f"PB_ORG:{powerbank_org_id}|ST_ORG:{station_org_id}|"
                           f"REASON:{reason}")
            
    except Exception as e:
        # В случае ошибки логирования просто выводим в консоль
        print(f"Ошибка логирования события выплева: {e}")


async def can_user_borrow_powerbank(db_pool, user_id: int, powerbank_id: int) -> tuple[bool, str]:
    """
    Проверяет, может ли пользователь взять указанный повербанк
    
    """
    try:
        from models.user_role import UserRole
        from models.powerbank import Powerbank
        
        # Получаем основную роль пользователя
        user_role = await UserRole.get_primary_role(db_pool, user_id)
        if not user_role:
            return False, "У пользователя нет назначенных ролей"
        
        # Глобальный администратор может взять любой повербанк
        if user_role.role == 'service_admin':
            return True, f"Глобальный администратор имеет доступ ко всем повербанкам"
        
        # Получаем повербанк
        powerbank = await Powerbank.get_by_id(db_pool, powerbank_id)
        if not powerbank:
            return False, "Повербанк не найден"
        
        # Проверяем статус повербанка
        if powerbank.status not in ['active', 'unknown']:
            return False, f"Повербанк недоступен (статус: {powerbank.status})"
        
        # Если у роли нет привязки к org_unit, доступ запрещен
        if user_role.org_unit_id is None:
            return False, "Роль пользователя не привязана к организационной единице"
        
        # Если у повербанка нет привязки к org_unit, доступ запрещен
        if powerbank.org_unit_id is None:
            return False, "Повербанк не привязан к организационной единице"
        
        # Проверяем совместимость организационных единиц
        compatible = await is_powerbank_compatible(
            db_pool, user_role.org_unit_id, powerbank.org_unit_id
        )
        
        if compatible:
            reason = await get_compatibility_reason(
                db_pool, user_role.org_unit_id, powerbank.org_unit_id
            )
            return True, f"Доступ разрешен: {reason}"
        else:
            reason = await get_compatibility_reason(
                db_pool, user_role.org_unit_id, powerbank.org_unit_id
            )
            return False, f"Повербанк недоступен вашему подразделению: {reason}"
        
    except Exception as e:
        return False, f"Ошибка проверки прав доступа: {e}"


async def can_user_access_station(db_pool, user_id: int, station_id: int) -> tuple[bool, str]:
    """
    Проверяет, может ли пользователь получить доступ к станции
    
    """
    try:
        from models.user_role import UserRole
        from models.station import Station
        
        # Получаем основную роль пользователя
        user_role = await UserRole.get_primary_role(db_pool, user_id)
        if not user_role:
            return False, "У пользователя нет назначенных ролей"
        
        # Глобальный администратор может получить доступ к любой станции
        if user_role.role == 'service_admin':
            return True, "Глобальный администратор имеет доступ ко всем станциям"
        
        # Получаем станцию
        station = await Station.get_by_id(db_pool, station_id)
        if not station:
            return False, "Станция не найдена"
        
        # Если у роли нет привязки к org_unit, доступ запрещен
        if user_role.org_unit_id is None:
            return False, "Роль пользователя не привязана к организационной единице"
        
        # Если у станции нет привязки к org_unit, доступ запрещен
        if station.org_unit_id is None:
            return False, "Станция не привязана к организационной единице"
        
        # Проверяем совместимость организационных единиц
        compatible = await is_powerbank_compatible(
            db_pool, user_role.org_unit_id, station.org_unit_id
        )
        
        if compatible:
            reason = await get_compatibility_reason(
                db_pool, user_role.org_unit_id, station.org_unit_id
            )
            return True, f"Доступ к станции разрешен: {reason}"
        else:
            reason = await get_compatibility_reason(
                db_pool, user_role.org_unit_id, station.org_unit_id
            )
            return False, f"Станция недоступна вашему подразделению: {reason}"
        
    except Exception as e:
        return False, f"Ошибка проверки доступа к станции: {e}"


async def log_access_denied_event(db_pool, user_id: int, resource_type: str, 
                                resource_id: int, reason: str) -> None:
    """
    Логирует событие отказа в доступе
    """
    try:
        logger = get_logger('access_control')
        logger.warning(f"ОТКАЗ В ДОСТУПЕ: пользователь {user_id}, {resource_type} {resource_id}, "
                      f"причина: {reason}")
        
        # Дополнительное структурированное логирование
        access_logger = get_logger('access_denied')
        access_logger.warning(f"ACCESS_DENIED|{get_moscow_time().isoformat()}|"
                            f"USER:{user_id}|RESOURCE:{resource_type.upper()}:{resource_id}|"
                            f"REASON:{reason}")
    except Exception as e:
        print(f"Ошибка логирования отказа в доступе: {e}")


async def get_admin_accessible_org_units(db_pool, user_id: int) -> Optional[list[int]]:
    """
    Получает список ID организационных единиц, доступных администратору.
    
    Returns:
        - None: если service_admin (доступ ко всем)
        - list[int]: список доступных org_unit_id для group_admin/subgroup_admin
        - []: если нет прав администратора
    """
    try:
        import aiomysql
        from models.user_role import UserRole
        
        # Получаем основную роль пользователя
        user_role = await UserRole.get_primary_role(db_pool, user_id)
        if not user_role:
            return []
        
        # service_admin видит всё
        if user_role.role == 'service_admin':
            return None
        
        # group_admin и subgroup_admin видят только свою единицу и дочерние
        if user_role.role in ['group_admin', 'subgroup_admin']:
            if user_role.org_unit_id is None:
                return []
            
            # Получаем текущую org_unit и все дочерние (без WITH RECURSIVE для MySQL 5.7)
            accessible_units = [user_role.org_unit_id]
            
            async with db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Получаем все org_units
                    await cur.execute("""
                        SELECT org_unit_id, parent_org_unit_id
                        FROM org_unit
                    """)
                    
                    all_units = await cur.fetchall()
                    
                    # Строим дерево в памяти и находим все дочерние единицы
                    def find_children(parent_id, all_units, visited=None):
                        if visited is None:
                            visited = set()
                        
                        if parent_id in visited:
                            return []
                        
                        visited.add(parent_id)
                        children = []
                        
                        for unit in all_units:
                            # Пропускаем самоссылающиеся единицы
                            if unit['parent_org_unit_id'] == parent_id and unit['org_unit_id'] != parent_id:
                                children.append(unit['org_unit_id'])
                                # Рекурсивно ищем детей
                                children.extend(find_children(unit['org_unit_id'], all_units, visited))
                        
                        return children
                    
                    # Находим все дочерние единицы
                    children = find_children(user_role.org_unit_id, all_units)
                    accessible_units.extend(children)
                    
                    # Убираем дубликаты
                    accessible_units = list(set(accessible_units))
            
            return accessible_units
        
        # Для остальных ролей доступа нет
        return []
        
    except Exception as e:
        print(f"Ошибка получения доступных org_units для администратора {user_id}: {e}")
        return []