# 🔄 Логика возврата повербанка

## Протокол 3.5 Return Power Bank and Response

### Процесс:

```
Пользователь вставляет повербанк в станцию
              ↓
Станция детектирует вставку
              ↓
┌──────────────────────────────────────────────────────┐
│ 3.5.1 Cabinet → Server (Request)                     │
│ Станция отправляет данные о повербанке:              │
│ - Slot, TerminalID, Level, Voltage, Current,         │
│   Temperature, Status, SOH                           │
└──────────────────────────────────────────────────────┘
              ↓
Сервер обрабатывает запрос
              ↓
┌──────────────────────────────────────────────────────┐
│ 3.5.2 Server → Cabinet (Response)                    │
│ Сервер отвечает станции:                             │
│ - Slot, Result (0-5), TerminalID, Level, Voltage,    │
│   Current, Temperature, Status, SOH                  │
└──────────────────────────────────────────────────────┘
              ↓
Станция получает Result и действует соответственно
```

---

## Логика обработки (server):

### 1. Проверка TerminalID
```python
if not terminal_id:
    return Result = 4  # Invalid Power Bank ID
```

### 2. Проверка повербанка в БД
```python
powerbank = await Powerbank.get_by_serial(terminal_id)

if not powerbank:
    # Повербанк НЕ НАЙДЕН → создаем со статусом 'unknown'
    powerbank = await Powerbank.create_unknown(terminal_id, org_unit_id)
    # Продолжаем обработку с новым повербанком
```

### 3. Проверка слота
```python
existing = await StationPowerbank.get_by_station_and_slot(station_id, slot)

if existing:
    return Result = 5  # Slot not empty
```

### 4. Проверка активного заказа
```python
active_order = await Order.get_active_borrow_order(powerbank_id)

if active_order:
    # Закрываем заказ: status='borrow' → status='return'
    await Order.update_order_status(order_id, 'return')
```

### 5. Добавление в station_powerbank
```python
await StationPowerbank.add_powerbank(
    station_id, powerbank_id, slot,
    level, voltage, temperature
)
```

### 6. Обновление станции
```python
await station.update_last_seen()
await station.update_remain_num(remain_num + 1)
```

### 7. Ответ станции
```python
return Result = 1  # Success
```

---

## Коды результата (Result):

| Код | Значение | Когда отправляется |
|-----|----------|-------------------|
| 0 | Failure | Общий сбой |
| **1** | **Success** | ✅ Повербанк успешно принят |
| 2 | Power Bank Status Error | Аномальный статус батареи |
| 3 | Duplicate Return | Повторный возврат |
| **4** | **Invalid Power Bank ID** | ⚠️ Повербанк НЕ НАЙДЕН в БД → не отдается |
| **5** | **Slot not empty** | ⚠️ Слот уже занят |

---

## Файлы:

- `optimized_server2/handlers/return_powerbank.py` - обработчик
- `optimized_server2/server.py:237-244` - точка входа
- `optimized_server2/utils/packet_utils.py` - парсинг/построение пакетов

---

## База данных:

### Таблица `orders`:
```sql
-- Если есть активный заказ (status='borrow')
UPDATE orders 
SET status='return', completed_at=NOW() 
WHERE order_id=X AND status='borrow'
```

### Таблица `station_powerbank`:
```sql
-- Добавляем повербанк в станцию
INSERT INTO station_powerbank 
(station_id, powerbank_id, slot_number, level, voltage, temperature)
VALUES (13, 53, 3, 85, 4100, 25)
```

### Таблица `station`:
```sql
-- Обновляем количество доступных повербанков
UPDATE station 
SET remain_num = remain_num + 1,
    last_seen = NOW()
WHERE station_id=13
```

---

**Дата:** 14 октября 2025  
**Версия протокола:** 3.5 Return Power Bank and Response

