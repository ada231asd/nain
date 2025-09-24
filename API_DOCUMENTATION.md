# API Документация для фронтенда

## Общая информация

**Базовый URL:** `http://localhost:8080`  
**Протокол:** HTTP/HTTPS  
**Формат данных:** JSON  
**Авторизация:** JWT Bearer Token

## Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке:
```
Authorization: Bearer <your_jwt_token>
```

---

## 1. АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ

### 1.1 Регистрация пользователя
**POST** `/api/auth/register`

Создает нового пользователя со статусом `pending`. Пароль отправляется на email.

**Тело запроса:**
```json
{
  "phone_e164": "+79001234567",
  "email": "user@example.com",
  "fio": "Иванов Иван Иванович"
}
```

**Ответ (200):**
```json
{
  "message": "Пользователь зарегистрирован. Пароль отправлен на email. Ожидает подтверждения администратора.",
  "user_id": 123,
  "status": "pending"
}
```

**Ошибки:**
- `400` - Отсутствуют обязательные поля
- `500` - Ошибка отправки email

### 1.2 Авторизация пользователя
**POST** `/api/auth/login`

Авторизация по номеру телефона и паролю. Доступно только для пользователей со статусом `active`.

**Тело запроса:**
```json
{
  "phone_e164": "+79001234567",
  "password": "your_password"
}
```

**Ответ (200):**
```json
{
  "message": "Успешная авторизация",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "user_id": 123,
    "phone_e164": "+79001234567",
    "email": "user@example.com",
    "fio": "Иванов Иван Иванович",
    "status": "active",
    "role": "user"
  }
}
```

**Ошибки:**
- `400` - Отсутствуют обязательные поля
- `401` - Неверные данные или пользователь не подтвержден
- `500` - Ошибка сервера

### 1.3 Получение профиля пользователя
**GET** `/api/auth/profile`

Получает информацию о текущем пользователе.

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ (200):**
```json
{
  "user": {
    "user_id": 123,
    "phone_e164": "+79001234567",
    "email": "user@example.com",
    "fio": "Иванов Иван Иванович",
    "status": "active",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T12:00:00Z"
  }
}
```

**Ошибки:**
- `401` - Токен не предоставлен или недействителен
- `404` - Пользователь не найден

### 1.4 Обновление профиля пользователя
**PUT** `/api/auth/profile`

Обновляет данные профиля пользователя.

**Заголовки:**
```
Authorization: Bearer <token>
```

**Тело запроса:**
```json
{
  "fio": "Новое ФИО",
  "email": "newemail@example.com"
}
```

**Ответ (200):**
```json
{
  "message": "Профиль обновлен",
  "user": {
    "user_id": 123,
    "phone_e164": "+79001234567",
    "email": "newemail@example.com",
    "fio": "Новое ФИО",
    "status": "active",
    "role": "user"
  }
}
```

---

## 2. АДМИНИСТРИРОВАНИЕ

### 2.1 Список пользователей на подтверждение
**GET** `/api/admin/pending-users`

Получает список пользователей со статусом `pending` (только для администраторов).

**Заголовки:**
```
Authorization: Bearer <admin_token>
```

**Ответ (200):**
```json
{
  "users": [
    {
      "user_id": 123,
      "phone_e164": "+79001234567",
      "email": "user@example.com",
      "fio": "Иванов Иван Иванович",
      "status": "pending",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Ошибки:**
- `401` - Токен не предоставлен или недействителен
- `403` - Недостаточно прав доступа

### 2.2 Подтверждение пользователя
**POST** `/api/admin/approve-user`

Подтверждает пользователя (меняет статус на `active`).

**Заголовки:**
```
Authorization: Bearer <admin_token>
```

**Тело запроса:**
```json
{
  "user_id": 123
}
```

**Ответ (200):**
```json
{
  "message": "Пользователь подтвержден"
}
```

### 2.3 Отклонение пользователя
**POST** `/api/admin/reject-user`

Отклоняет пользователя (меняет статус на `blocked`).

**Заголовки:**
```
Authorization: Bearer <admin_token>
```

**Тело запроса:**
```json
{
  "user_id": 123
}
```

**Ответ (200):**
```json
{
  "message": "Пользователь отклонен"
}
```

### 2.4 Управление повербанками (админ)

#### 2.4.1 Список неизвестных повербанков
**GET** `/api/admin/unknown-powerbanks`

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "serial_number": "PB001",
      "status": "unknown",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

#### 2.4.2 Активация повербанка
**POST** `/api/admin/activate-powerbank`

**Тело запроса:**
```json
{
  "powerbank_id": 1,
  "admin_user_id": 123,
  "target_org_unit_id": 1
}
```

#### 2.4.3 Деактивация повербанка
**POST** `/api/admin/deactivate-powerbank`

**Тело запроса:**
```json
{
  "powerbank_id": 1,
  "admin_user_id": 123,
  "reason": "admin_deactivated"
}
```

#### 2.4.4 Статус повербанка
**GET** `/api/admin/powerbank-status/{powerbank_id}`

#### 2.4.5 Массовая активация
**POST** `/api/admin/bulk-activate-powerbanks`

**Тело запроса:**
```json
{
  "powerbank_ids": [1, 2, 3],
  "admin_user_id": 123,
  "target_org_unit_id": 1
}
```

#### 2.4.6 Статистика повербанков
**GET** `/api/admin/powerbank-statistics`

#### 2.4.7 Принудительное извлечение
**POST** `/api/admin/force-eject-powerbank`

**Тело запроса:**
```json
{
  "station_id": 1,
  "slot_number": 5,
  "admin_user_id": 123
}
```

---

## 3. ВЫДАЧА ПОВЕРБАНКОВ

### 3.1 Список доступных повербанков в станции
**GET** `/api/borrow/stations/{station_id}/powerbanks`

**Параметры URL:**
- `station_id` (int) - ID станции

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "powerbank_id": 1,
      "serial_number": "PB001",
      "slot_number": 5,
      "soh": 85,
      "status": "active"
    }
  ]
}
```

### 3.2 Статус слота
**GET** `/api/borrow/stations/{station_id}/slots/{slot_number}/status`

**Параметры URL:**
- `station_id` (int) - ID станции
- `slot_number` (int) - Номер слота

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "slot_number": 5,
    "status": "occupied",
    "powerbank_id": 1,
    "serial_number": "PB001"
  }
}
```

### 3.3 Запрос на выдачу повербанка
**POST** `/api/borrow/stations/{station_id}/request`

**Параметры URL:**
- `station_id` (int) - ID станции

**Тело запроса:**
```json
{
  "slot_number": 5,
  "user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос на выдачу отправлен",
  "data": {
    "order_id": 456,
    "powerbank_id": 1,
    "slot_number": 5
  }
}
```

### 3.4 Информация о станции
**GET** `/api/borrow/stations/{station_id}/info`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "name": "Станция №1",
    "location": "Москва, ул. Примерная, 1",
    "total_slots": 20,
    "available_slots": 15,
    "status": "online"
  }
}
```

### 3.5 Выбор оптимального повербанка
**GET** `/api/borrow/stations/{station_id}/select-optimal`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "powerbank_id": 1,
    "serial_number": "PB001",
    "slot_number": 5,
    "soh": 95,
    "reason": "highest_charge"
  }
}
```

### 3.6 Запрос оптимальной выдачи
**POST** `/api/borrow/stations/{station_id}/request-optimal`

**Тело запроса:**
```json
{
  "user_id": 123
}
```

### 3.7 Запрос выдачи по ID повербанка
**POST** `/api/borrow/powerbanks/{powerbank_id}/request`

**Тело запроса:**
```json
{
  "user_id": 123
}
```

---

## 4. CRUD API - ПОЛЬЗОВАТЕЛИ

### 4.1 Создать пользователя
**POST** `/api/users`

**Тело запроса:**
```json
{
  "fio": "Иванов Иван Иванович",
  "phone_e164": "+79001234567",
  "email": "user@example.com",
  "role": "user",
  "статус": "active",
  "password": "password123",
  "parent_org_unit_id": 1
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 123},
  "message": "Пользователь создан"
}
```

### 4.2 Получить список пользователей
**GET** `/api/users?page=1&limit=10&status=active&org_unit_id=1`

**Параметры запроса:**
- `page` (int) - Номер страницы (по умолчанию 1)
- `limit` (int) - Количество записей на странице (по умолчанию 10)
- `status` (string) - Фильтр по статусу
- `org_unit_id` (int) - Фильтр по организационной единице

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "user_id": 123,
      "fio": "Иванов Иван Иванович",
      "phone_e164": "+79001234567",
      "email": "user@example.com",
      "status": "active",
      "role": "user",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  }
}
```

### 4.3 Получить пользователя по ID
**GET** `/api/users/{user_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "fio": "Иванов Иван Иванович",
    "phone_e164": "+79001234567",
    "email": "user@example.com",
    "status": "active",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 4.4 Обновить пользователя
**PUT** `/api/users/{user_id}`

**Тело запроса:**
```json
{
  "fio": "Новое ФИО",
  "email": "newemail@example.com",
  "status": "active"
}
```

### 4.5 Удалить пользователя
**DELETE** `/api/users/{user_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Пользователь удален"
}
```

---

## 5. CRUD API - СТАНЦИИ

### 5.1 Создать станцию
**POST** `/api/stations`

**Тело запроса:**
```json
{
  "name": "Станция №1",
  "location": "Москва, ул. Примерная, 1",
  "total_slots": 20,
  "org_unit_id": 1,
  "status": "active"
}
```

### 5.2 Получить список станций
**GET** `/api/stations?page=1&limit=10&status=active&org_unit_id=1`

### 5.3 Получить станцию по ID
**GET** `/api/stations/{station_id}`

### 5.4 Обновить станцию
**PUT** `/api/stations/{station_id}`

### 5.5 Удалить станцию
**DELETE** `/api/stations/{station_id}`

---

## 6. CRUD API - ПОВЕРБАНКИ

### 6.1 Создать повербанк
**POST** `/api/powerbanks`

**Тело запроса:**
```json
{
  "serial_number": "PB001",
  "org_unit_id": 1,
  "soh": 100,
  "status": "unknown",
  "write_off_reason": "none"
}
```

### 6.2 Получить список повербанков
**GET** `/api/powerbanks?page=1&limit=10&status=active&org_unit_id=1`

### 6.3 Получить повербанк по ID
**GET** `/api/powerbanks/{powerbank_id}`

### 6.4 Обновить повербанк
**PUT** `/api/powerbanks/{powerbank_id}`

### 6.5 Удалить повербанк
**DELETE** `/api/powerbanks/{powerbank_id}`

---

## 7. CRUD API - ЗАКАЗЫ

### 7.1 Создать заказ
**POST** `/api/orders`

**Тело запроса:**
```json
{
  "station_id": 1,
  "user_id": 123,
  "powerbank_id": 1,
  "status": "borrow"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 456},
  "message": "Заказ создан"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: station_id"
}
```

**Ответ (400) - Недопустимый статус:**
```json
{
  "success": false,
  "error": "Недопустимый статус заказа. Допустимые значения: borrow, return"
}
```

**Ответ (400) - Станция не найдена:**
```json
{
  "success": false,
  "error": "Станция не найдена"
}
```

**Ответ (400) - Пользователь не найден:**
```json
{
  "success": false,
  "error": "Пользователь не найден"
}
```

### 7.2 Получить список заказов
**GET** `/api/orders?page=1&limit=10&status=borrow&user_id=123&station_id=1`

**Параметры запроса:**
- `page` (int) - Номер страницы (по умолчанию 1)
- `limit` (int) - Количество записей на странице (по умолчанию 10)
- `status` (string) - Фильтр по статусу
- `user_id` (int) - Фильтр по пользователю
- `station_id` (int) - Фильтр по станции

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 456,
      "station_id": 1,
      "user_id": 123,
      "powerbank_id": 1,
      "status": "borrow",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50,
    "pages": 5
  }
}
```

**Ответ (200) - Пустой список:**
```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 0,
    "pages": 0
  }
}
```

### 7.3 Получить заказ по ID
**GET** `/api/orders/{order_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "station_id": 1,
    "user_id": 123,
    "powerbank_id": 1,
    "status": "borrow",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Ответ (404) - Заказ не найден:**
```json
{
  "success": false,
  "error": "Заказ не найден"
}
```

### 7.4 Обновить заказ
**PUT** `/api/orders/{order_id}`

**Тело запроса:**
```json
{
  "status": "return",
  "powerbank_id": 1
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "station_id": 1,
    "user_id": 123,
    "powerbank_id": 1,
    "status": "return"
  },
  "message": "Заказ обновлен"
}
```

**Ответ (404) - Заказ не найден:**
```json
{
  "success": false,
  "error": "Заказ не найден"
}
```

### 7.5 Удалить заказ
**DELETE** `/api/orders/{order_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Заказ удален"
}
```

**Ответ (404) - Заказ не найден:**
```json
{
  "success": false,
  "error": "Заказ не найден"
}
```

---

## 8. CRUD API - ОРГАНИЗАЦИОННЫЕ ЕДИНИЦЫ

### 8.1 Создать организационную единицу
**POST** `/api/org-units`

**Тело запроса:**
```json
{
  "name": "Отдел продаж",
  "parent_org_unit_id": 1,
  "description": "Описание отдела"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Организационная единица создана"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: name"
}
```

### 8.2 Получить список организационных единиц
**GET** `/api/org-units?page=1&limit=10`

**Параметры запроса:**
- `page` (int) - Номер страницы (по умолчанию 1)
- `limit` (int) - Количество записей на странице (по умолчанию 10)

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "org_unit_id": 1,
      "name": "Отдел продаж",
      "parent_org_unit_id": null,
      "description": "Описание отдела",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50,
    "pages": 5
  }
}
```

### 8.3 Получить организационную единицу по ID
**GET** `/api/org-units/{org_unit_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "org_unit_id": 1,
    "name": "Отдел продаж",
    "parent_org_unit_id": null,
    "description": "Описание отдела",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Ответ (404) - Организационная единица не найдена:**
```json
{
  "success": false,
  "error": "Организационная единица не найдена"
}
```

### 8.4 Обновить организационную единицу
**PUT** `/api/org-units/{org_unit_id}`

**Тело запроса:**
```json
{
  "name": "Обновленный отдел продаж",
  "description": "Новое описание отдела"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "org_unit_id": 1,
    "name": "Обновленный отдел продаж",
    "parent_org_unit_id": null,
    "description": "Новое описание отдела"
  },
  "message": "Организационная единица обновлена"
}
```

### 8.5 Удалить организационную единицу
**DELETE** `/api/org-units/{org_unit_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Организационная единица удалена"
}
```

**Ответ (404) - Организационная единица не найдена:**
```json
{
  "success": false,
  "error": "Организационная единица не найдена"
}
```

---

## 9. CRUD API - РОЛИ ПОЛЬЗОВАТЕЛЕЙ

### 9.1 Создать роль пользователя
**POST** `/api/user-roles`

**Тело запроса:**
```json
{
  "user_id": 123,
  "role": "group_admin",
  "org_unit_id": 1
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Роль пользователя создана"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: user_id"
}
```

### 9.2 Получить список ролей пользователей
**GET** `/api/user-roles?page=1&limit=10`

**Параметры запроса:**
- `page` (int) - Номер страницы (по умолчанию 1)
- `limit` (int) - Количество записей на странице (по умолчанию 10)

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "role_id": 1,
      "user_id": 123,
      "role": "group_admin",
      "org_unit_id": 1,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50,
    "pages": 5
  }
}
```

### 9.3 Удалить роль пользователя
**DELETE** `/api/user-roles/{role_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Роль пользователя удалена"
}
```

**Ответ (404) - Роль не найдена:**
```json
{
  "success": false,
  "error": "Роль пользователя не найдена"
}
```

---

## 10. CRUD API - ИЗБРАННЫЕ СТАНЦИИ

### 10.1 Добавить станцию в избранное
**POST** `/api/user-favorites`

**Тело запроса:**
```json
{
  "user_id": 123,
  "station_id": 1
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Станция добавлена в избранное"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: user_id"
}
```

### 10.2 Получить избранные станции пользователя
**GET** `/api/user-favorites?user_id=123`

**Параметры запроса:**
- `user_id` (int) - ID пользователя

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "favorite_id": 1,
      "user_id": 123,
      "station_id": 1,
      "station_name": "Станция №1",
      "station_location": "Москва, ул. Примерная, 1",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 10.3 Удалить из избранного
**DELETE** `/api/user-favorites/{favorite_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Станция удалена из избранного"
}
```

**Ответ (404) - Избранное не найдено:**
```json
{
  "success": false,
  "error": "Избранное не найдено"
}
```

---

## 11. CRUD API - СВЯЗИ СТАНЦИЯ-ПОВЕРБАНК

### 11.1 Создать связь станция-powerbank
**POST** `/api/station-powerbanks`

**Тело запроса:**
```json
{
  "station_id": 1,
  "powerbank_id": 1,
  "slot_number": 5
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Связь станция-powerbank создана"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: station_id"
}
```

### 11.2 Получить связи станция-powerbank
**GET** `/api/station-powerbanks?station_id=1&powerbank_id=1`

**Параметры запроса:**
- `station_id` (int) - ID станции (опционально)
- `powerbank_id` (int) - ID повербанка (опционально)

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "sp_id": 1,
      "station_id": 1,
      "powerbank_id": 1,
      "slot_number": 5,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 11.3 Удалить связь
**DELETE** `/api/station-powerbanks/{sp_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Связь удалена"
}
```

**Ответ (404) - Связь не найдена:**
```json
{
  "success": false,
  "error": "Связь не найдена"
}
```

---

## 12. CRUD API - СЕКРЕТНЫЕ КЛЮЧИ СТАНЦИЙ

### 12.1 Создать секретный ключ станции
**POST** `/api/station-secret-keys`

**Тело запроса:**
```json
{
  "station_id": 1,
  "secret_key": "secret123"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Секретный ключ станции создан"
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: station_id"
}
```

### 12.2 Получить секретные ключи станций
**GET** `/api/station-secret-keys?station_id=1`

**Параметры запроса:**
- `station_id` (int) - ID станции (опционально)

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "key_id": 1,
      "station_id": 1,
      "secret_key": "secret123",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 12.3 Удалить секретный ключ
**DELETE** `/api/station-secret-keys/{key_id}`

**Ответ (200):**
```json
{
  "success": true,
  "message": "Секретный ключ удален"
}
```

**Ответ (404) - Ключ не найден:**
```json
{
  "success": false,
  "error": "Секретный ключ не найден"
}
```

### 12.4 Удалить секретный ключ по station_id
**DELETE** `/api/station-secret-keys?station_id=1`

**Параметры запроса:**
- `station_id` (int) - ID станции

**Ответ (200):**
```json
{
  "success": true,
  "message": "Секретный ключ станции удален"
}
```

---

## 13. ИНВЕНТАРЬ СТАНЦИЙ (0x64)

### 13.1 Получить инвентарь станции
**GET** `/api/inventory/stations/{station_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "slots": [
      {
        "slot_number": 1,
        "status": "occupied",
        "powerbank_id": 1,
        "serial_number": "PB001",
        "soh": 85
      }
    ],
    "total_slots": 20,
    "occupied_slots": 15,
    "available_slots": 5
  }
}
```

**Ответ (404) - Станция не найдена:**
```json
{
  "success": false,
  "error": "Станция не найдена"
}
```

### 13.2 Запросить инвентарь через TCP
**POST** `/api/inventory/stations/{station_id}/query`

**Тело запроса:**
```json
{
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос инвентаря отправлен",
  "data": {
    "station_id": 1,
    "request_id": "req_123456"
  }
}
```

**Ответ (400) - Отсутствует admin_user_id:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: admin_user_id"
}
```

### 13.3 Детали слота
**GET** `/api/inventory/stations/{station_id}/slots/{slot_number}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "slot_number": 1,
    "status": "occupied",
    "powerbank_id": 1,
    "serial_number": "PB001",
    "soh": 85,
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

**Ответ (404) - Слот не найден:**
```json
{
  "success": false,
  "error": "Слот не найден"
}
```

### 13.4 Сводка по инвентарю
**GET** `/api/inventory/summary`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "total_stations": 10,
    "total_slots": 200,
    "occupied_slots": 150,
    "available_slots": 50,
    "stations_online": 8,
    "stations_offline": 2
  }
}
```

---

## 14. УДАЛЕННАЯ ПЕРЕЗАГРУЗКА СТАНЦИЙ (0x67)

### 14.1 Перезагрузить станцию
**POST** `/api/restart/stations/{station_id}`

**Тело запроса:**
```json
{
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Команда перезагрузки отправлена",
  "data": {
    "station_id": 1,
    "request_id": "restart_123456"
  }
}
```

**Ответ (400) - Отсутствует admin_user_id:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: admin_user_id"
}
```

### 14.2 Массовая перезагрузка станций
**POST** `/api/restart/stations/bulk`

**Тело запроса:**
```json
{
  "station_ids": [1, 2, 3],
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Команды перезагрузки отправлены",
  "data": {
    "station_ids": [1, 2, 3],
    "request_ids": ["restart_123456", "restart_123457", "restart_123458"]
  }
}
```

**Ответ (400) - Неверные данные:**
```json
{
  "success": false,
  "error": "station_ids должен быть непустым массивом"
}
```

---

## 15. ЗАПРОС АДРЕСА СЕРВЕРА (0x6A)

### 15.1 Запросить адрес сервера
**POST** `/api/server-address/stations/{station_id}/query`

**Тело запроса:**
```json
{
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос адреса сервера отправлен",
  "data": {
    "station_id": 1,
    "request_id": "addr_123456"
  }
}
```

### 15.2 Получить адрес сервера
**GET** `/api/server-address/stations/{station_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "server_address": "192.168.1.100",
    "port": 8080,
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

**Ответ (404) - Адрес не найден:**
```json
{
  "success": false,
  "error": "Адрес сервера не найден"
}
```

---

## 16. УСТАНОВКА АДРЕСА СЕРВЕРА (0x63)

### 16.1 Установить адрес сервера
**POST** `/api/set-server-address/stations/{station_id}/set`

**Тело запроса:**
```json
{
  "server_address": "192.168.1.100",
  "port": 8080,
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Команда установки адреса сервера отправлена",
  "data": {
    "station_id": 1,
    "server_address": "192.168.1.100",
    "port": 8080,
    "request_id": "set_addr_123456"
  }
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: server_address"
}
```

### 16.2 Получить результат установки
**GET** `/api/set-server-address/stations/{station_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "status": "success",
    "server_address": "192.168.1.100",
    "port": 8080,
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Ответ (404) - Результат не найден:**
```json
{
  "success": false,
  "error": "Результат установки не найден"
}
```

---

## 17. УПРАВЛЕНИЕ ГРОМКОСТЬЮ ГОЛОСОВОГО ВЕЩАНИЯ (0x77, 0x70)

### 17.1 Запросить уровень громкости
**POST** `/api/voice-volume/stations/{station_id}/query`

**Тело запроса:**
```json
{
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос уровня громкости отправлен",
  "data": {
    "station_id": 1,
    "request_id": "volume_123456"
  }
}
```

### 17.2 Установить уровень громкости
**POST** `/api/voice-volume/stations/{station_id}/set`

**Тело запроса:**
```json
{
  "volume_level": 50,
  "admin_user_id": 123
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Команда установки громкости отправлена",
  "data": {
    "station_id": 1,
    "volume_level": 50,
    "request_id": "set_volume_123456"
  }
}
```

**Ответ (400) - Неверный уровень громкости:**
```json
{
  "success": false,
  "error": "Уровень громкости должен быть от 0 до 100"
}
```

### 17.3 Получить уровень громкости
**GET** `/api/voice-volume/stations/{station_id}`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "volume_level": 50,
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

### 17.4 Получить результат установки
**GET** `/api/voice-volume/stations/{station_id}/setting`

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 1,
    "status": "success",
    "volume_level": 50,
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## 18. ПОЛЬЗОВАТЕЛЬСКИЕ API

### 18.1 Доступные повербанки для пользователя
**GET** `/api/user/powerbanks/available`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "station_id": 1,
      "station_name": "Станция №1",
      "station_location": "Москва, ул. Примерная, 1",
      "powerbanks": [
        {
          "powerbank_id": 1,
          "serial_number": "PB001",
          "slot_number": 5,
          "soh": 85,
          "status": "active"
        }
      ]
    }
  ]
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

### 18.2 Заказы пользователя
**GET** `/api/user/orders`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 456,
      "station_id": 1,
      "station_name": "Станция №1",
      "powerbank_id": 1,
      "serial_number": "PB001",
      "status": "borrow",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

### 18.3 Взять повербанк
**POST** `/api/user/powerbanks/borrow`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Тело запроса:**
```json
{
  "station_id": 1,
  "slot_number": 5
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос на выдачу повербанка отправлен",
  "data": {
    "order_id": 456,
    "powerbank_id": 1,
    "station_id": 1,
    "slot_number": 5
  }
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: station_id"
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

### 18.4 Вернуть повербанк
**POST** `/api/user/powerbanks/return`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Тело запроса:**
```json
{
  "station_id": 1,
  "slot_number": 5
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Запрос на возврат повербанка отправлен",
  "data": {
    "order_id": 456,
    "powerbank_id": 1,
    "station_id": 1,
    "slot_number": 5
  }
}
```

**Ответ (400) - Отсутствуют обязательные поля:**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: station_id"
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

### 18.5 Список станций
**GET** `/api/user/stations`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ (200):**
```json
{
  "success": true,
  "data": [
    {
      "station_id": 1,
      "name": "Станция №1",
      "location": "Москва, ул. Примерная, 1",
      "total_slots": 20,
      "available_slots": 15,
      "status": "online",
      "distance": 1.5
    }
  ]
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

### 18.6 Профиль пользователя
**GET** `/api/user/profile`

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "phone_e164": "+79001234567",
    "email": "user@example.com",
    "fio": "Иванов Иван Иванович",
    "status": "active",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T12:00:00Z"
  }
}
```

**Ответ (401) - Не авторизован:**
```json
{
  "success": false,
  "error": "Токен авторизации не предоставлен"
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Неверные данные запроса |
| 401 | Не авторизован |
| 403 | Недостаточно прав доступа |
| 404 | Ресурс не найден |
| 500 | Внутренняя ошибка сервера |

## Статусы пользователей

- `pending` - Ожидает подтверждения администратора
- `active` - Активный пользователь
- `blocked` - Заблокированный пользователь

## Роли пользователей

- `user` - Обычный пользователь
- `subgroup_admin` - Администратор подгруппы
- `group_admin` - Администратор группы
- `service_admin` - Администратор сервиса

## Статусы повербанков

- `active` - Активный
- `user_reported_broken` - Сломан (сообщил пользователь)
- `system_error` - Ошибка системы
- `written_off` - Списано
- `unknown` - Неизвестный статус

## Статусы заказов

- `borrow` - Взятие повербанка
- `return` - Возврат повербанка
