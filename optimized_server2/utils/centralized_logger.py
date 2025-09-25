"""
Централизованный логгер для избежания утечек файловых дескрипторов
"""
import logging
import os
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
    """Настраивает основной логгер"""
    global _main_logger
    
    # Создаем папку для логов, если её нет
    os.makedirs('logs', exist_ok=True)
    
    # Создаем основной логгер
    _main_logger = logging.getLogger('tcp_server')
    _main_logger.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики
    _main_logger.handlers.clear()
    
    # Создаем обработчик для записи в файл
    handler = logging.FileHandler('logs/server.log', encoding='utf-8')
    handler.setLevel(logging.INFO)
    
    # Создаем форматтер
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Добавляем обработчик к основному логгеру
    _main_logger.addHandler(handler)
    
    # Также добавляем вывод в консоль для отладки
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    _main_logger.addHandler(console_handler)

def close_logger():
    """Закрывает все обработчики логгера"""
    global _main_logger
    if _main_logger:
        for handler in _main_logger.handlers:
            handler.close()
        _main_logger.handlers.clear()
        _main_logger = None
