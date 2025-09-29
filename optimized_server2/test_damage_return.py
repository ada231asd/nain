#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API возврата повербанка с поломкой
"""
import asyncio
import aiohttp
import json

async def test_damage_return_api():
    """Тестирует API возврата повербанка с поломкой"""
    
    # URL API
    url = "http://localhost:8080/api/return-damage"
    
    # Тестовые данные
    test_data = {
        "station_id": 13,  # ID станции
        "description": "Повербанк не заряжается, кабель поврежден"  # Описание проблемы
    }
    
    # Заголовки (нужен JWT токен)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"  # Замените на реальный токен
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Отправляем запрос на {url}")
            print(f"Данные: {json.dumps(test_data, indent=2)}")
            
            async with session.post(url, json=test_data, headers=headers) as response:
                print(f"Статус ответа: {response.status}")
                
                response_text = await response.text()
                print(f"Ответ сервера: {response_text}")
                
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get('success'):
                        print("✅ Возврат с поломкой выполнен успешно!")
                        print(f"Order ID: {response_data.get('order_id')}")
                        print(f"Powerbank ID: {response_data.get('powerbank_id')}")
                        print(f"Station ID: {response_data.get('station_id')}")
                        print(f"Powerbank Inserted: {response_data.get('powerbank_inserted', 'N/A')}")
                        print(f"Message: {response_data.get('message')}")
                        
                        if response_data.get('powerbank_inserted'):
                            print("🎯 Повербанк успешно обнаружен в станции!")
                        else:
                            print("⚠️  Повербанк не был обнаружен в станции. Проверьте правильность вставки.")
                    else:
                        print(f"❌ Ошибка: {response_data.get('error', 'Неизвестная ошибка')}")
                else:
                    print(f"❌ HTTP ошибка: {response.status}")
                    
    except Exception as e:
        print(f"❌ Ошибка выполнения запроса: {e}")

async def test_without_auth():
    """Тестирует API без авторизации (должна быть ошибка 401)"""
    
    url = "http://localhost:8080/api/return-damage"
    test_data = {
        "station_id": 13,
        "description": "Тест без авторизации"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\nТестируем без авторизации...")
            
            async with session.post(url, json=test_data) as response:
                print(f"Статус ответа: {response.status}")
                response_text = await response.text()
                print(f"Ответ сервера: {response_text}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🧪 Тестирование API возврата повербанка с поломкой")
    print("=" * 50)
    
    # Запускаем тесты
    asyncio.run(test_damage_return_api())
    asyncio.run(test_without_auth())
    
    print("\n📝 Инструкции по использованию:")
    print("1. Убедитесь, что сервер запущен на localhost:8080")
    print("2. Получите JWT токен через API авторизации")
    print("3. Замените YOUR_JWT_TOKEN_HERE на реальный токен")
    print("4. Убедитесь, что у пользователя есть активный заказ")
    print("5. Убедитесь, что станция с ID 13 подключена")
