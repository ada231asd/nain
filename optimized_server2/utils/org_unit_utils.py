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
    
    Правила совместимости:
    1. Один и тот же org_unit - совместимы
    2. Повербанк в группе (родитель), станция в подгруппе этой группы - совместимы
    3. Все остальные случаи - несовместимы
    
    Args:
        db_pool: Пул соединений с БД
        powerbank_org_id: ID организационной единицы повербанка
        station_org_id: ID организационной единицы станции
        
    Returns:
        bool: True если совместимы, False если нет
    """
    try:
        powerbank_unit = await OrgUnit.get_by_id(db_pool, powerbank_org_id)
        station_unit = await OrgUnit.get_by_id(db_pool, station_org_id)

        if not powerbank_unit or not station_unit:
            return False

        # 1. Один и тот же org_unit
        if powerbank_unit.org_unit_id == station_unit.org_unit_id:
            return True

        # 2. Повербанк в группе (родитель), станция в подгруппе этой группы
        if (powerbank_unit.unit_type == 'group' and 
            station_unit.parent_org_unit_id == powerbank_unit.org_unit_id):
            return True

        # 3. Все остальные случаи несовместимы
        return False
        
    except Exception as e:
        # В случае ошибки считаем несовместимыми для безопасности
        print(f"Ошибка проверки совместимости org_unit: {e}")
        return False


async def get_compatibility_reason(db_pool, powerbank_org_id: int, station_org_id: int) -> str:
    """
    Возвращает причину совместимости/несовместимости для логирования
    
    Args:
        db_pool: Пул соединений с БД
        powerbank_org_id: ID организационной единицы повербанка
        station_org_id: ID организационной единицы станции
        
    Returns:
        str: Описание причины
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
    
    Args:
        db_pool: Пул соединений с БД (не используется, оставлен для совместимости)
        station_id: ID станции
        slot_number: Номер слота
        powerbank_serial: Серийный номер повербанка
        powerbank_org_id: ID организационной единицы повербанка
        station_org_id: ID организационной единицы станции
        reason: Причина выплева
    """
    try:
        # Логируем в файл через централизованный логгер
        logger = get_logger('powerbank_ejection')
        
        # Детальное логирование события выплева
        logger.info(f"ВЫПЛЕВ ПОВЕРБАНКА: станция {station_id}, слот {slot_number}, "
                   f"повербанк {powerbank_serial} (org_unit: {powerbank_org_id}), "
                   f"станция org_unit: {station_org_id}, причина: {reason}")
        
        # Дополнительно логируем в отдельный файл для выплевов (если нужно)
        ejection_logger = get_logger('powerbank_ejections')
        ejection_logger.info(f"EJECTION|{get_moscow_time().isoformat()}|"
                           f"STATION:{station_id}|SLOT:{slot_number}|"
                           f"POWERBANK:{powerbank_serial}|"
                           f"PB_ORG:{powerbank_org_id}|ST_ORG:{station_org_id}|"
                           f"REASON:{reason}")
            
    except Exception as e:
        # В случае ошибки логирования просто выводим в консоль
        print(f"Ошибка логирования события выплева: {e}")
