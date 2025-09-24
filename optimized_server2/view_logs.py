#!/usr/bin/env python3
"""
Скрипт для просмотра логов пакетов
"""

import os
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

def view_logs(log_dir: str = "logs", log_type: str = "human", limit: int = 50):
    """
    Просматривает логи пакетов
    
    Args:
        log_dir: Директория с логами
        log_type: Тип логов ('human', 'incoming', 'outgoing')
        limit: Количество записей для показа
    """
    
    if not os.path.exists(log_dir):
        print(f"❌ Директория {log_dir} не найдена")
        return
    
    # Ищем файлы логов
    log_files = []
    for file in os.listdir(log_dir):
        if file.startswith(f"packets_{log_type}") and file.endswith(".log"):
            log_files.append(os.path.join(log_dir, file))
    
    if not log_files:
        print(f"❌ Файлы логов типа '{log_type}' не найдены")
        print(f"Доступные файлы в {log_dir}:")
        for file in os.listdir(log_dir):
            if file.endswith(".log"):
                print(f"  - {file}")
        return
    
    # Сортируем файлы по дате (новые первыми)
    log_files.sort(reverse=True)
    
    print(f"📋 Просмотр логов типа '{log_type}' (последние {limit} записей)")
    print(f"📁 Директория: {log_dir}")
    print("=" * 80)
    
    total_entries = 0
    
    for log_file in log_files:
        if total_entries >= limit:
            break
            
        print(f"\n📄 Файл: {os.path.basename(log_file)}")
        print("-" * 40)
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                if log_type == "human":
                    # Для человеко-читаемых логов просто выводим содержимое
                    content = f.read()
                    lines = content.split('\n')
                    for line in lines[-limit*20:]:  # Примерно 20 строк на запись
                        if line.strip():
                            print(line)
                else:
                    # Для JSON логов парсим и выводим
                    entries = []
                    current_entry = ""
                    for line in f:
                        if line.strip() == "-" * 80:
                            if current_entry.strip():
                                try:
                                    entry = json.loads(current_entry)
                                    entries.append(entry)
                                except json.JSONDecodeError:
                                    pass
                            current_entry = ""
                        else:
                            current_entry += line
                    
                    # Показываем последние записи
                    for entry in entries[-limit:]:
                        total_entries += 1
                        if total_entries > limit:
                            break
                            
                        print(f"\n🕐 {entry.get('timestamp', 'Unknown time')}")
                        print(f"📤 {entry.get('direction', 'Unknown').upper()}")
                        print(f"🔧 {entry.get('command_name', 'Unknown')} ({entry.get('command', 'Unknown')})")
                        print(f"📏 {entry.get('size', 0)} байт")
                        
                        station_info = entry.get('station_info', {})
                        if station_info:
                            print(f"🏢 Станция: {station_info.get('box_id', 'unknown')} (ID: {station_info.get('station_id', 'unknown')})")
                        
                        print(f"🔢 HEX: {entry.get('hex_data', 'Unknown')[:50]}{'...' if len(entry.get('hex_data', '')) > 50 else ''}")
                        
                        parsed_data = entry.get('parsed_data', {})
                        if parsed_data and len(parsed_data) > 0:
                            print("📋 Данные:")
                            for key, value in parsed_data.items():
                                if key not in ['RawPacket', 'ReceivedAt'] and value is not None:
                                    print(f"   {key}: {value}")
                        
                        print("-" * 40)
                        
        except Exception as e:
            print(f"❌ Ошибка чтения файла {log_file}: {e}")
    
    print(f"\n✅ Показано {total_entries} записей")

def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        log_type = sys.argv[1]
    else:
        log_type = "human"
    
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            limit = 50
    else:
        limit = 50
    
    print("🔍 Просмотр логов пакетов")
    print("Использование: python view_logs.py [тип] [количество]")
    print("Типы: human, incoming, outgoing")
    print("Пример: python view_logs.py human 20")
    print()
    
    view_logs("logs", log_type, limit)

if __name__ == "__main__":
    main()
