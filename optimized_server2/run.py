#!/usr/bin/env python3
"""
Скрипт для запуска системы управления повербанками
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from server import OptimizedServer


async def main():
    """Главная функция запуска системы"""
   
    
    try:
        # Создаем экземпляр сервера
        server = OptimizedServer()
        
        print(" Инициализация сервера...")
        await server.initialize_database()
        
      
        
        print("\n Запуск сервера...")
        
        # Запускаем сервер
        await server.start_servers()
        
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
    except Exception as e:
        print(f"\n Ошибка запуска: {e}")
        sys.exit(1)
    finally:
        print("\n Остановка сервера...")
        if 'server' in locals():
            await server.stop_servers()
        print(" Сервер остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
    except Exception as e:
        print(f"\n Критическая ошибка: {e}")
        sys.exit(1)