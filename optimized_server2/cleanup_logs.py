#!/usr/bin/env python3
"""
Скрипт для очистки старых логов
"""

import os
import glob
from datetime import datetime, timedelta

def cleanup_logs(log_dir: str = "logs", days_to_keep: int = 7):
    """
    Удаляет старые файлы логов
    
    Args:
        log_dir: Директория с логами
        days_to_keep: Количество дней для хранения логов
    """
    
    if not os.path.exists(log_dir):
        print(f" Директория {log_dir} не найдена")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    total_size = 0
    
    print(f" Очистка логов старше {days_to_keep} дней")
    print(f" Удаляем файлы старше: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Директория: {log_dir}")
    print("=" * 60)
    
    # Ищем все файлы логов
    log_patterns = [
        os.path.join(log_dir, "packets_*.log"),
        os.path.join(log_dir, "*.log")
    ]
    
    for pattern in log_patterns:
        for log_file in glob.glob(pattern):
            try:
                # Получаем время модификации файла
                file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                
                if file_mtime < cutoff_date:
                    file_size = os.path.getsize(log_file)
                    total_size += file_size
                    
                    print(f"  Удаляем: {os.path.basename(log_file)}")
                    print(f"   Размер: {file_size / 1024:.1f} KB")
                    print(f"   Дата: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    os.remove(log_file)
                    deleted_count += 1
                else:
                    print(f" Оставляем: {os.path.basename(log_file)} ({file_mtime.strftime('%Y-%m-%d')})")
                    
            except Exception as e:
                print(f" Ошибка обработки файла {log_file}: {e}")
    
    print("=" * 60)
    print(f" Удалено файлов: {deleted_count}")
    print(f" Освобождено места: {total_size / 1024 / 1024:.2f} MB")

def show_log_stats(log_dir: str = "logs"):
    """Показывает статистику логов"""
    
    if not os.path.exists(log_dir):
        print(f" Директория {log_dir} не найдена")
        return
    
    print(f" Статистика логов в {log_dir}")
    print("=" * 50)
    
    total_files = 0
    total_size = 0
    file_types = {}
    
    for file in os.listdir(log_dir):
        if file.endswith(".log"):
            file_path = os.path.join(log_dir, file)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            total_files += 1
            
            # Определяем тип файла
            if "incoming" in file:
                file_type = "Входящие"
            elif "outgoing" in file:
                file_type = "Исходящие"
            elif "human" in file:
                file_type = "Человеко-читаемые"
            else:
                file_type = "Другие"
            
            if file_type not in file_types:
                file_types[file_type] = {"count": 0, "size": 0}
            
            file_types[file_type]["count"] += 1
            file_types[file_type]["size"] += file_size
            
            print(f" {file}")
            print(f"   Размер: {file_size / 1024:.1f} KB")
            print(f"   Тип: {file_type}")
            print()
    
    print("=" * 50)
    print(f" Общая статистика:")
    print(f"   Всего файлов: {total_files}")
    print(f"   Общий размер: {total_size / 1024 / 1024:.2f} MB")
    print()
    
    for file_type, stats in file_types.items():
        print(f"   {file_type}: {stats['count']} файлов, {stats['size'] / 1024:.1f} KB")

def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "stats"
    
    if command == "clean":
        days = 7
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print(" Неверное количество дней")
                return
        
        cleanup_logs("logs", days)
    elif command == "stats":
        show_log_stats("logs")
    else:
        print(" Утилита очистки логов")
        print("Использование:")
        print("  python cleanup_logs.py stats          - показать статистику")
        print("  python cleanup_logs.py clean [дни]    - очистить старые логи")
        print("Пример: python cleanup_logs.py clean 3  - удалить логи старше 3 дней")

if __name__ == "__main__":
    main()
