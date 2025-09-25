"""
Централизованный логгер для минимизации файловых дескрипторов
Использует только один файловый дескриптор для всего сервера
"""
import logging
import logging.handlers
import os
import sys
from typing import Optional

# Глобальный логгер
_main_logger: Optional[logging.Logger] = None

def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер с указанным именем.
    Все логгеры используют один файловый дескриптор.
    """
    global _main_logger
    
    # Создаем основной логгер только один раз
    if _main_logger is None:
        _setup_main_logger()
    
    # Создаем дочерний логгер с указанным именем
    logger = _main_logger.getChild(name)
    return logger

def _setup_main_logger():
    """Настраивает основной логгер с ротацией и оптимизацией"""
    global _main_logger
    
    # Создаем папку для логов, если её нет
    os.makedirs('logs', exist_ok=True)
    
    # Создаем основной логгер
    _main_logger = logging.getLogger('tcp_server')
    _main_logger.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики
    _main_logger.handlers.clear()
    
    # Создаем ротирующий обработчик для записи в файл
    # Максимум 10MB на файл, сохраняем 5 файлов
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/server.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Создаем форматтер с более компактным форматом
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Добавляем обработчик к основному логгеру
    _main_logger.addHandler(file_handler)
    
    # Добавляем вывод в консоль только в режиме отладки
    if os.getenv('DEBUG', 'false').lower() == 'true':
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        _main_logger.addHandler(console_handler)
    
    # Предотвращаем дублирование сообщений
    _main_logger.propagate = False

def close_logger():
    """Закрывает все обработчики логгера"""
    global _main_logger
    if _main_logger:
        for handler in _main_logger.handlers:
            handler.close()
        _main_logger.handlers.clear()
        _main_logger = None

def get_logger_stats() -> dict:
    """Возвращает статистику использования логгера"""
    global _main_logger
    if not _main_logger:
        return {"handlers": 0, "children": 0}
    
    return {
        "handlers": len(_main_logger.handlers),
        "children": len(_main_logger.manager.loggerDict),
        "level": _main_logger.level
    }
