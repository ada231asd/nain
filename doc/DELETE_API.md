# API Удаления Данных

## 1. Мягкое удаление записи

**Описание:** Помечает запись как удаленную, но сохраняет в БД. При удалении пользователя статус меняется на `blocked`.

**Запрос:**
```
DELETE /api/soft-delete/{entity_type}/{entity_id}
```

**Пример ответа:**
```json
{
  "success": true,
  "message": "Пользователь успешно удален",
  "deletedAt": "2025-10-28 15:30:45"
}
```

---

## 2. Восстановление записи

**Описание:** Восстанавливает удаленную запись. При восстановлении пользователя статус меняется на `active`.

**Запрос:**
```
POST /api/soft-delete/restore/{entity_type}/{entity_id}
```

**Пример ответа:**
```json
{
  "success": true,
  "message": "Пользователь успешно восстановлен"
}
```

---

## 3. Список удаленных записей

**Описание:** Получает список всех удаленных записей определенного типа с пагинацией.

**Запрос:**
```
GET /api/soft-delete/{entity_type}?limit=10&offset=0
```

**Пример ответа:**
```json
{
  "success": true,
  "records": [
    {
      "userId": 123,
      "name": "Alex",
      "email": "alex@example.com",
      "deletedAt": "2025-10-28 15:30:45",
      "status": "blocked"
    },
    {
      "userId": 124,
      "name": "John",
      "email": "john@example.com",
      "deletedAt": "2025-10-27 10:15:20",
      "status": "blocked"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

---

## 4. Статистика удаленных записей

**Описание:** Возвращает количество удаленных записей по всем типам сущностей.

**Запрос:**
```
GET /api/soft-delete/statistics
```

**Пример ответа:**
```json
{
  "success": true,
  "statistics": {
    "users": 25,
    "stations": 5,
    "powerbanks": 12,
    "orders": 150,
    "org_units": 3,
    "user_roles": 8,
    "user_favorites": 45,
    "total": 248
  }
}
```

---

## 5. Жесткое удаление записи (только service_admin)

**Описание:** Физически удаляет запись из БД навсегда. Операция необратима.

**Запрос:**
```
DELETE /api/hard-delete/{entity_type}/{entity_id}
```

**Тело запроса:**
```json
{
  "confirm": true
}
```

**Пример ответа:**
```json
{
  "success": true,
  "message": "Пользователь физически удален из базы данных",
  "userId": 123
}
```

---

## 6. Предпросмотр очистки старых записей

**Описание:** Показывает список записей, которые будут удалены при очистке (старше N дней).

**Запрос:**
```
GET /api/hard-delete/cleanup/preview?entity_type=user&days_old=90
```

**Пример ответа:**
```json
{
  "success": true,
  "entityType": "user",
  "daysOld": 90,
  "totalCandidates": 15,
  "preview": [
    {
      "userId": 100,
      "name": "Old User 1",
      "email": "old1@example.com",
      "deletedAt": "2025-05-15 10:20:30",
      "status": "blocked"
    },
    {
      "userId": 101,
      "name": "Old User 2",
      "email": "old2@example.com",
      "deletedAt": "2025-05-10 08:15:00",
      "status": "blocked"
    }
  ]
}
```

---

## 7. Массовая очистка старых записей (только service_admin)

**Описание:** Физически удаляет все записи, удаленные более N дней назад.

**Запрос:**
```
DELETE /api/hard-delete/cleanup
```

**Тело запроса:**
```json
{
  "entityType": "user",
  "daysOld": 90,
  "confirm": true
}
```

**Пример ответа:**
```json
{
  "success": true,
  "message": "Очистка выполнена",
  "deletedCount": 15,
  "entityType": "user",
  "daysOld": 90
}
```

---

## Поддерживаемые типы сущностей (entity_type)

- `user` - пользователи
- `station` - станции
- `powerbank` - повербанки
- `org_unit` - организационные единицы
- `order` - заказы
- `user_role` - роли пользователей
- `user_favorite` - избранные станции
- `slot_report` - отчеты об аномалиях слотов

---

## ⚠️ Важно

- **Мягкое удаление пользователя:** статус → `blocked`, можно восстановить
- **Восстановление пользователя:** статус → `active`
- **Жесткое удаление:** требует `service_admin` + `confirm: true`
- **Все запросы:** требуют авторизации через Bearer token

