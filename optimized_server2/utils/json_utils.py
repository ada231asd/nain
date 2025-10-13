"""
Утилиты для работы с JSON сериализацией
"""
import json
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, List


def convert_datetime_to_string(obj: Any) -> Any:
    """
    Конвертирует datetime объекты в строки для JSON сериализации
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, str):
        # Удаляем нулевые байты из строк
        return obj.rstrip('\x00')
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    else:
        return obj


def serialize_for_json(data: Any) -> Any:
    """
    Сериализует данные для JSON, конвертируя datetime объекты в строки
    """
    return convert_datetime_to_string(data)


def safe_json_response(data: Dict[str, Any], status: int = 200) -> Dict[str, Any]:
    #сериализация данных для JSON ответа
    try:
        serialized_data = serialize_for_json(data)
        return {
            "data": serialized_data,
            "status": status
        }
    except Exception as e:
        return {
            "data": {
                "success": False,
                "error": f"Ошибка сериализации JSON: {str(e)}"
            },
            "status": 500
        }

from aiohttp import web
from typing import Any, Dict


def json_ok(data: Any = None, status: int = 200, **extra: Any) -> web.Response:
    """Возвращает стандартный успешный JSON ответ в формате {success, data, ...}."""
    payload: Dict[str, Any] = {"success": True, "data": data}
    if extra:
        payload.update(extra)
    return web.json_response(serialize_for_json(payload), status=status)


def json_fail(error: str, status: int = 400, **extra: Any) -> web.Response:
    """Возвращает стандартный ошибочный JSON ответ в формате {success: False, error, ...}."""
    payload: Dict[str, Any] = {"success": False, "error": error}
    if extra:
        payload.update(extra)
    return web.json_response(serialize_for_json(payload), status=status)