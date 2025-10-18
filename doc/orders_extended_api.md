# API для работы с заказами с использованием v_orders_extended

## Обзор

Этот API предоставляет расширенные возможности для работы с заказами, используя представление `v_orders_extended` из базы данных. API интегрирован с существующей ролевой архитектурой системы, где разные роли пользователей имеют доступ к разным endpoints.

## Ролевая архитектура

### 🔐 Роли пользователей:
- **Обычные пользователи** (`user`) - могут брать повербанки в аренду
- **Администраторы групп** (`group_admin`) - управляют повербанками в своей группе
- **Администраторы подгрупп** (`subgroup_admin`) - управляют повербанками в своей подгруппе  
- **Сервис-администраторы** (`service_admin`) - полный доступ ко всем операциям

### 📊 Структура представления v_orders_extended

```sql
CREATE VIEW v_orders_extended AS 
SELECT 
    o.id AS id,
    pb.serial_number AS powerbank_serial,
    o.status AS status,
    o.timestamp AS timestamp,
    o.completed_at AS completed_at,
    COALESCE(uf.nik, s.box_id) AS station_display_name,
    ou.name AS org_unit_name,
    ou.adress AS org_unit_address,
    u.fio AS user_fio,
    u.phone_e164 AS user_phone,
    o.user_id AS user_id,
    o.station_id AS station_id,
    o.org_unit_id AS org_unit_id,
    o.powerbank_id AS powerbank_id
FROM orders o
LEFT JOIN station s ON o.station_id = s.station_id
LEFT JOIN org_unit ou ON o.org_unit_id = ou.org_unit_id
LEFT JOIN app_user u ON o.user_id = u.user_id
LEFT JOIN powerbank pb ON o.powerbank_id = pb.id
LEFT JOIN user_favorites uf ON (o.user_id = uf.user_id AND o.station_id = uf.station_id)
```

## API Endpoints по ролям

### 👤 API для обычных пользователей (`UserPowerbankAPI`)

#### 1. Получение заказов пользователя

**GET** `/api/user/orders`

Получает заказы текущего пользователя с расширенными данными из `v_orders_extended`.

**Аутентификация:** JWT токен обязателен

**Ответ:**
```json
{
    "success": true,
    "orders": [
        {
            "id": 102,
            "powerbank_serial": "DCHA54000016",
            "status": "borrow",
            "timestamp": "2025-10-18T14:30:18",
            "completed_at": null,
            "station_display_name": "Моя любимая станция",
            "org_unit_name": "Офис",
            "org_unit_address": "ул. Примерная, д. 1",
            "user_fio": "Вадим Вадимвич Базаров",
            "user_phone": "+79013344076",
            "user_id": 33,
            "station_id": 16,
            "org_unit_id": 1,
            "powerbank_id": 55
        }
    ]
}
```

#### 2. Выдача повербанка (сервер выбирает оптимальный)

**POST** `/api/user/powerbanks/borrow`

Сервер автоматически выбирает оптимальный повербанк из доступных.

**Параметры запроса:**
```json
{
    "station_id": 1
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Повербанк успешно выдан",
    "order_id": 123,
    "powerbank": {
        "powerbank_id": 1,
        "serial_number": "PB001"
    }
}
```

### 🔧 API для администраторов (`AdminPowerbankAPI`)

#### 1. Создание административного заказа

**POST** `/api/orders`

Создает заказ администратором с расширенными данными через общий endpoint с флагом `is_admin_order`.

**Параметры запроса:**
```json
{
    "station_id": 1,
    "user_id": 1,
    "powerbank_id": 1,
    "org_unit_id": 1,
    "status": "force_eject",
    "is_admin_order": true,
    "admin_user_id": 1
}
```

**Ответ:**
```json
{
    "success": true,
    "data": {
        "id": 123,
        "extended_data": {
            "id": 123,
            "powerbank_serial": "PB001",
            "status": "force_eject",
            "timestamp": "2025-01-18T10:30:00",
            "completed_at": null,
            "station_display_name": "Станция 1",
            "org_unit_name": "Офис",
            "org_unit_address": "ул. Примерная, д. 1",
            "user_fio": "Админ Админов",
            "user_phone": "+7123456789",
            "user_id": 1,
            "station_id": 1,
            "org_unit_id": 1,
            "powerbank_id": 1
        },
        "is_admin_order": true
    },
    "message": "Заказ создан успешно"
}
```

#### 2. Получение административных заказов

**GET** `/api/orders/extended`

Получает заказы администратора с расширенными данными через общий endpoint с фильтрацией.

**Параметры запроса:**
- `user_id` (int) - ID администратора для фильтрации
- `limit` (int, по умолчанию: 50) - количество записей
- `offset` (int, по умолчанию: 0) - смещение

**Ответ:**
```json
{
    "success": true,
    "data": [
        {
            "id": 102,
            "powerbank_serial": "PB001",
            "status": "force_eject",
            "timestamp": "2025-01-18T10:30:00",
            "completed_at": null,
            "station_display_name": "Станция 1",
            "org_unit_name": "Офис",
            "org_unit_address": "ул. Примерная, д. 1",
            "user_fio": "Админ Админов",
            "user_phone": "+7123456789",
            "user_id": 1,
            "station_id": 1,
            "org_unit_id": 1,
            "powerbank_id": 1
        }
    ],
    "pagination": {
        "total": 25,
        "limit": 50,
        "offset": 0
    },
    "extended": true
}
```

#### 3. Принудительная выдача повербанка

**POST** `/api/admin/force-eject-powerbank`

Принудительно выдает повербанк из указанного слота станции.

**Параметры запроса:**
```json
{
    "station_id": 1,
    "slot_number": 2,
    "admin_user_id": 1
}
```

### 📋 Общий CRUD API для заказов (`OrdersCRUD`)

#### 1. Создание заказа

**POST** `/api/orders`

Создает новый заказ с расширенной валидацией.

**Параметры запроса:**
```json
{
    "station_id": 1,
    "user_id": 1,
    "powerbank_id": 1,
    "org_unit_id": 1,
    "status": "borrow"
}
```

#### 2. Получение заказов

**GET** `/api/orders`

Получает список заказов с возможностью использования расширенных данных.

**Параметры запроса:**
- `extended` (boolean) - использовать расширенные данные из `v_orders_extended`
- `page` (int) - номер страницы
- `limit` (int) - количество записей на странице
- `status` (string) - фильтр по статусу
- `user_id` (int) - фильтр по пользователю
- `station_id` (int) - фильтр по станции

#### 3. Получение расширенных заказов

**GET** `/api/orders/extended`

Специальный endpoint для получения только расширенных данных заказов.

## Модель Order - новые методы

### get_extended_by_id(db_pool, order_id)
Получает расширенные данные заказа по ID из представления `v_orders_extended`.

### get_extended_by_user_id(db_pool, user_id, limit=50, offset=0)
Получает расширенные данные заказов пользователя с пагинацией.

### get_extended_by_station_id(db_pool, station_id, limit=50, offset=0)
Получает расширенные данные заказов станции с пагинацией.

### get_extended_by_status(db_pool, status, limit=50, offset=0)
Получает расширенные данные заказов по статусу с пагинацией.

### search_extended_orders(db_pool, filters, limit=50, offset=0)
Поиск заказов с расширенными данными по фильтрам.

## Поля представления v_orders_extended

### Основные поля заказа:
- `id` - ID заказа
- `status` - статус заказа (borrow, return, force_eject)
- `timestamp` - время создания заказа
- `completed_at` - время завершения заказа

### Данные повербанка:
- `powerbank_serial` - серийный номер повербанка
- `powerbank_id` - ID повербанка

### Данные станции:
- `station_display_name` - отображаемое название станции (персональное или box_id)
- `station_id` - ID станции

### Данные организации:
- `org_unit_name` - название организационной единицы
- `org_unit_address` - адрес организационной единицы
- `org_unit_id` - ID организационной единицы

### Данные пользователя:
- `user_fio` - ФИО пользователя
- `user_phone` - телефон пользователя
- `user_id` - ID пользователя

## Интеграция с существующими API

### 🔄 Автоматическая интеграция

1. **UserPowerbankAPI.get_user_orders()** - теперь использует `Order.get_extended_by_user_id()`
2. **AdminPowerbankAPI** - добавлены методы для работы с расширенными данными
3. **OrdersCRUD** - поддерживает параметр `extended=true` для всех endpoints

### 🎯 Преимущества интеграции

1. **Единообразие данных**: Все API теперь возвращают одинаковую структуру расширенных данных
2. **Персонализация**: Отображаются персональные названия станций из избранного
3. **Производительность**: Использование оптимизированного представления БД
4. **Обратная совместимость**: Старые endpoints продолжают работать

## Примеры использования

### Получение истории заказов пользователя
```javascript
// Frontend запрос
const response = await fetch('/api/user/orders', {
    headers: {
        'Authorization': `Bearer ${jwt_token}`
    }
});
const data = await response.json();

// Результат содержит расширенные данные:
// - id (ID заказа)
// - powerbank_serial
// - station_display_name (персональное название)
// - org_unit_name, org_unit_address
// - user_fio, user_phone
// - user_id, station_id, org_unit_id, powerbank_id
```

### Создание административного заказа
```javascript
const adminOrder = await fetch('/api/orders', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${admin_jwt_token}`
    },
    body: JSON.stringify({
        station_id: 1,
        user_id: 1,
        powerbank_id: 1,
        org_unit_id: 1,
        status: 'force_eject',
        is_admin_order: true,
        admin_user_id: 1
    })
});
```

### Получение заказов с расширенными данными
```javascript
// Использование общего API с параметром extended
const orders = await fetch('/api/orders?extended=true&status=borrow');

// Или специальный endpoint для расширенных данных
const extendedOrders = await fetch('/api/orders/extended?status=borrow');
```

## Обработка ошибок

Все API возвращают стандартные HTTP коды состояния:

- `200` - Успешный запрос
- `400` - Ошибка валидации данных
- `401` - Не авторизован (для endpoints с JWT)
- `403` - Доступ запрещен (недостаточно прав)
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера

## Безопасность

1. **JWT аутентификация** - обязательна для пользовательских endpoints
2. **Ролевая авторизация** - проверка прав доступа к операциям
3. **Валидация данных** - все входные данные проверяются
4. **Логирование действий** - все административные операции логируются
