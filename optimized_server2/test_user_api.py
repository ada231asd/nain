#!/usr/bin/env python3
"""
Тестирование API пользователей с новым форматом JSON
"""
import asyncio
import aiohttp
import json

async def test_user_api():
    """Тестирует API пользователей"""
    base_url = "http://localhost:8080"
    
    # Тестовые данные
    test_user_data = {
        "fio": "Тестовый Пользователь",
        "phone_e164": "+7 (999) 123-45-67",
        "email": "test@example.com",
        "role": "user",
        "parent_org_unit_id": "1",
        "статус": "active",
        "password": "testpassword123"
    }
    
    test_update_data = {
        "fio": "Обновленный Пользователь",
        "phone_e164": "+7 (999) 123-45-67",
        "email": "updated@example.com",
        "role": "subgroup_admin",
        "parent_org_unit_id": "2",
        "статус": "active"
    }
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Тестирование API пользователей")
        print("=" * 50)
        
        # 1. Тест создания пользователя
        print("\n1️⃣ Тест создания пользователя")
        print(f"Данные: {json.dumps(test_user_data, ensure_ascii=False, indent=2)}")
        
        async with session.post(f"{base_url}/api/users", json=test_user_data) as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                user_id = response_data['data']['user_id']
                print(f"✅ Пользователь создан с ID: {user_id}")
            else:
                print("❌ Ошибка создания пользователя")
                return
        
        # 2. Тест получения пользователя
        print(f"\n2️⃣ Тест получения пользователя {user_id}")
        
        async with session.get(f"{base_url}/api/users/{user_id}") as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                print("✅ Пользователь получен")
            else:
                print("❌ Ошибка получения пользователя")
        
        # 3. Тест обновления пользователя
        print(f"\n3️⃣ Тест обновления пользователя {user_id}")
        print(f"Данные: {json.dumps(test_update_data, ensure_ascii=False, indent=2)}")
        
        async with session.put(f"{base_url}/api/users/{user_id}", json=test_update_data) as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                print("✅ Пользователь обновлен")
            else:
                print("❌ Ошибка обновления пользователя")
        
        # 4. Тест получения обновленного пользователя
        print(f"\n4️⃣ Тест получения обновленного пользователя {user_id}")
        
        async with session.get(f"{base_url}/api/users/{user_id}") as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                print("✅ Обновленный пользователь получен")
            else:
                print("❌ Ошибка получения обновленного пользователя")
        
        # 5. Тест получения списка пользователей
        print(f"\n5️⃣ Тест получения списка пользователей")
        
        async with session.get(f"{base_url}/api/users") as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                print(f"✅ Получен список пользователей: {len(response_data['data'])} пользователей")
            else:
                print("❌ Ошибка получения списка пользователей")
        
        # 6. Тест удаления пользователя
        print(f"\n6️⃣ Тест удаления пользователя {user_id}")
        
        async with session.delete(f"{base_url}/api/users/{user_id}") as resp:
            print(f"Статус: {resp.status}")
            response_data = await resp.json()
            print(f"Ответ: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if resp.status == 200 and response_data.get('success'):
                print("✅ Пользователь удален")
            else:
                print("❌ Ошибка удаления пользователя")
        
        print("\n" + "=" * 50)
        print("🏁 Тестирование завершено")

if __name__ == "__main__":
    asyncio.run(test_user_api())
