import asyncio
import aiohttp
import json

async def test_powerbank_borrow():
    # Данные для авторизации - пользователь 33 (group_admin)
    auth_data = {
        "phone_e164": "+79013344076",
        "password": "HVhcbsN4"
    }
    
    async with aiohttp.ClientSession() as session:
        print("=== ТЕСТ ВЫДАЧИ ПОВЕРБАНКА ===\n")
        
        # 1. Авторизация
        print("1. 🔐 АВТОРИЗАЦИЯ...")
        async with session.post(
            "http://localhost:8000/api/auth/login",
            json=auth_data
        ) as resp:
            auth_result = await resp.json()
            token = auth_result.get("token")
            if not token:
                print("❌ Ошибка авторизации:", auth_result)
                return
            print("✅ Токен получен")
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 2. Запрос доступных повербанков (до выдачи)
        print("\n2. 📋 ДОСТУПНЫЕ ПОВЕРБАНКИ (ДО ВЫДАЧИ)...")
        async with session.get(
            "http://localhost:8000/api/user/powerbanks/available",
            headers=headers
        ) as resp:
            result = await resp.json()
            if result.get('success'):
                data = result.get('data', {})
                limits = data.get('user_limits', {})
                print(f"   Лимиты: макс.{limits.get('max_limit')}, взято: {limits.get('current_borrowed')}, доступно: {limits.get('available_by_limit')}")
                print(f"   Количество доступных повербанков: {data.get('count', 0)}")
                for pb in data.get('available_powerbanks', []):
                    print(f"   - Powerbank {pb['powerbank_id']}: {pb['serial_number']} (SOH: {pb['soh']}%)")
            else:
                print("❌ Ошибка:", result.get('message'))

        # 3. Запрос списка станций
        print("\n3. 🏪 СПИСОК СТАНЦИЙ...")
        async with session.get(
            "http://localhost:8000/api/user/stations",
            headers=headers
        ) as resp:
            stations_result = await resp.json()
            station_id = None
            if stations_result.get('success'):
                stations = stations_result.get('data', {}).get('stations', [])
                active_stations = [s for s in stations if s.get('status') == 'active']
                if active_stations:
                    station_id = active_stations[0]['station_id']
                    station = active_stations[0]
                    print(f"   Выбрана станция: ID {station_id}, {station['box_id']}")
                    print(f"   Свободно: {station['remain_num']}/{station['slots_declared']} слотов")
                else:
                    print("❌ Нет активных станций")
                    return
            else:
                print("❌ Ошибка получения станций")
                return

        # 4. ВЫДАЧА ПОВЕРБАНКА
        print("\n4. 🚀 ВЫДАЧА ПОВЕРБАНКА...")
        if station_id:
            borrow_data = {"station_id": station_id}
            
            async with session.post(
                "http://localhost:8000/api/user/powerbanks/borrow",
                headers=headers,
                json=borrow_data
            ) as resp:
                borrow_result = await resp.json()
                if borrow_result.get('success'):
                    data = borrow_result.get('data', {})
                    print("✅ Выдача успешна!")
                    print(f"   Order ID: {data.get('order_id')}")
                    print(f"   Повербанк: {data.get('powerbank_serial')}")
                    print(f"   Станция: {data.get('station_box_id')}")
                    
                    # Показываем обновленные лимиты
                    limits = data.get('user_limits', {})
                    print(f"   Новые лимиты: макс.{limits.get('max_limit')}, взято: {limits.get('current_borrowed')}, доступно: {limits.get('available_by_limit')}")
                else:
                    print("❌ Ошибка выдачи:", borrow_result.get('message'))

        # 5. Проверяем доступные повербанки после выдачи
        print("\n5. 📊 ПРОВЕРКА ПОСЛЕ ВЫДАЧИ...")
        async with session.get(
            "http://localhost:8000/api/user/powerbanks/available",
            headers=headers
        ) as resp:
            result_after = await resp.json()
            if result_after.get('success'):
                data = result_after.get('data', {})
                limits = data.get('user_limits', {})
                print(f"   Лимиты: макс.{limits.get('max_limit')}, взято: {limits.get('current_borrowed')}, доступно: {limits.get('available_by_limit')}")
                print(f"   Количество доступных повербанков: {data.get('count', 0)}")
                for pb in data.get('available_powerbanks', []):
                    print(f"   - Powerbank {pb['powerbank_id']}: {pb['serial_number']} (SOH: {pb['soh']}%)")
            else:
                print("❌ Ошибка:", result_after.get('message'))

        # 6. Запрос заказов пользователя
        print("\n6. 📦 АКТИВНЫЕ ЗАКАЗЫ...")
        async with session.get(
            "http://localhost:8000/api/user/orders",
            headers=headers
        ) as resp:
            orders_result = await resp.json()
            if orders_result.get('success'):
                orders = orders_result.get('data', {}).get('orders', [])
                active_orders = [o for o in orders if o.get('status') == 'borrow']
                print(f"   Активных заказов: {len(active_orders)}")
                for order in active_orders:
                    print(f"   - Order {order['order_id']}: {order['powerbank']['serial_number']} (статус: {order['status']})")
            else:
                print("❌ Ошибка получения заказов")

        print("\n" + "="*50)
        print("🎯 ТЕСТ ЗАВЕРШЕН")

# Запуск теста
if __name__ == "__main__":
    asyncio.run(test_powerbank_borrow())