#!/usr/bin/env python3
"""
Тестовый скрипт для API избранных станций пользователей
"""
import asyncio
import aiohttp
import json
from datetime import datetime

# Конфигурация
BASE_URL = "http://localhost:8080"
TEST_USER_ID = 8  # ID пользователя из базы данных
TEST_STATION_ID = 1  # ID станции для тестирования

class UserFavoritesAPITester:
    """Тестер API для избранных станций"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_add_favorite(self, user_id: int, station_id: int):
        """Тест добавления станции в избранное"""
        print(f"\n🔵 Тест добавления станции {station_id} в избранное пользователя {user_id}")
        
        url = f"{self.base_url}/api/user-favorites"
        data = {
            "user_id": user_id,
            "station_id": station_id
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    async def test_get_favorites(self, user_id: int):
        """Тест получения избранных станций пользователя"""
        print(f"\n🔵 Тест получения избранных станций пользователя {user_id}")
        
        url = f"{self.base_url}/api/user-favorites?user_id={user_id}"
        
        try:
            async with self.session.get(url) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    async def test_delete_favorite(self, favorite_id: int):
        """Тест удаления станции из избранного"""
        print(f"\n🔵 Тест удаления записи {favorite_id} из избранного")
        
        url = f"{self.base_url}/api/user-favorites/{favorite_id}"
        
        try:
            async with self.session.delete(url) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    async def test_duplicate_favorite(self, user_id: int, station_id: int):
        """Тест попытки добавить дубликат в избранное"""
        print(f"\n🔵 Тест попытки добавить дубликат станции {station_id} в избранное")
        
        url = f"{self.base_url}/api/user-favorites"
        data = {
            "user_id": user_id,
            "station_id": station_id
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    async def test_invalid_user(self, station_id: int):
        """Тест добавления в избранное с несуществующим пользователем"""
        print(f"\n🔵 Тест добавления в избранное с несуществующим пользователем")
        
        url = f"{self.base_url}/api/user-favorites"
        data = {
            "user_id": 99999,  # Несуществующий пользователь
            "station_id": station_id
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    async def test_invalid_station(self, user_id: int):
        """Тест добавления в избранное несуществующей станции"""
        print(f"\n🔵 Тест добавления в избранное несуществующей станции")
        
        url = f"{self.base_url}/api/user-favorites"
        data = {
            "user_id": user_id,
            "station_id": 99999  # Несуществующая станция
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                print(f"Статус: {response.status}")
                print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования API избранных станций")
    print(f"📍 Базовый URL: {BASE_URL}")
    print(f"👤 Тестовый пользователь: {TEST_USER_ID}")
    print(f"🏢 Тестовая станция: {TEST_STATION_ID}")
    
    async with UserFavoritesAPITester(BASE_URL) as tester:
        # 1. Получаем текущие избранные станции
        print("\n" + "="*60)
        print("1. ПОЛУЧЕНИЕ ТЕКУЩИХ ИЗБРАННЫХ СТАНЦИЙ")
        print("="*60)
        await tester.test_get_favorites(TEST_USER_ID)
        
        # 2. Добавляем станцию в избранное
        print("\n" + "="*60)
        print("2. ДОБАВЛЕНИЕ СТАНЦИИ В ИЗБРАННОЕ")
        print("="*60)
        add_result = await tester.test_add_favorite(TEST_USER_ID, TEST_STATION_ID)
        
        # 3. Проверяем, что станция добавилась
        print("\n" + "="*60)
        print("3. ПРОВЕРКА ДОБАВЛЕНИЯ")
        print("="*60)
        favorites_result = await tester.test_get_favorites(TEST_USER_ID)
        
        # 4. Пытаемся добавить дубликат
        print("\n" + "="*60)
        print("4. ТЕСТ ДУБЛИКАТА")
        print("="*60)
        await tester.test_duplicate_favorite(TEST_USER_ID, TEST_STATION_ID)
        
        # 5. Тестируем невалидные данные
        print("\n" + "="*60)
        print("5. ТЕСТ НЕВАЛИДНЫХ ДАННЫХ")
        print("="*60)
        await tester.test_invalid_user(TEST_STATION_ID)
        await tester.test_invalid_station(TEST_USER_ID)
        
        # 6. Удаляем добавленную станцию из избранного
        if favorites_result and favorites_result.get('success') and favorites_result.get('data'):
            favorite_id = favorites_result['data'][0]['id']
            print("\n" + "="*60)
            print("6. УДАЛЕНИЕ СТАНЦИИ ИЗ ИЗБРАННОГО")
            print("="*60)
            await tester.test_delete_favorite(favorite_id)
            
            # 7. Проверяем, что станция удалилась
            print("\n" + "="*60)
            print("7. ПРОВЕРКА УДАЛЕНИЯ")
            print("="*60)
            await tester.test_get_favorites(TEST_USER_ID)
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
