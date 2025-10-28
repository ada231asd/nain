# API Мягкого и Жесткого Удаления

Документация для фронтенд-разработчиков

---

## 📋 Структура URL

```
/api/soft-delete/{entity_type}/{id}
                  ↑              ↑
             тип сущности    ID записи
```

**Где:**
- `{entity_type}` - тип сущности (user, station, powerbank и т.д.)
- `{id}` - ID конкретной записи

**Пример:**
```
DELETE /api/soft-delete/user/123
                       ↑     ↑
                     тип    ID пользователя
```

---

## 🗂️ Доступные типы сущностей

Мягкое удаление реализовано для следующих сущностей:

| Тип (`entity_type`) | Описание | Пример URL |
|---------------------|----------|------------|
| `user` | Пользователи | `/api/soft-delete/user/123` |
| `station` | Станции | `/api/soft-delete/station/45` |
| `powerbank` | Повербанки | `/api/soft-delete/powerbank/789` |
| `org_unit` | Организационные единицы | `/api/soft-delete/org_unit/5` |
| `order` | Заказы | `/api/soft-delete/order/1001` |
| `user_role` | Роли пользователей | `/api/soft-delete/user_role/10` |
| `user_favorite` | Избранные станции | `/api/soft-delete/user_favorite/25` |
| `slot_report` | Отчеты об аномалиях слотов | `/api/soft-delete/slot_report/50` |

---

## 1. Мягкое удаление записи

### Описание
Помечает запись как удаленную (`is_deleted = 1`), но оставляет в базе данных. Запись можно восстановить.

**⚠️ Важно для пользователей:** При удалении пользователя его статус автоматически меняется на `blocked` (заблокирован). При восстановлении статус возвращается в `active`.

### Запрос
```http
DELETE /api/soft-delete/user/123
Authorization: Bearer <token>
```

```json
{}
```

### Ответ
```json
{
  "success": true,
  "message": "Пользователь успешно удален",
  "deletedAt": "2025-10-28 15:30:45"
}
```

### Примеры для других сущностей

**Удаление станции:**
```http
DELETE /api/soft-delete/station/45
Authorization: Bearer <token>
```

**Удаление повербанка:**
```http
DELETE /api/soft-delete/powerbank/789
Authorization: Bearer <token>
```

**Удаление заказа:**
```http
DELETE /api/soft-delete/order/1001
Authorization: Bearer <token>
```

---

## 2. Восстановление записи

### Описание
Восстанавливает мягко удаленную запись.

### Запрос
```http
POST /api/soft-delete/restore/user/123
Authorization: Bearer <token>
```

```json
{}
```

### Ответ
```json
{
  "success": true,
  "message": "Пользователь успешно восстановлен"
}
```

---

## 3. Список удаленных записей

### Описание
Получает список всех мягко удаленных записей определенного типа.

### Запрос
```http
GET /api/soft-delete/user?limit=10&offset=0
Authorization: Bearer <token>
```

```json
{}
```

### Ответ
```json
{
  "success": true,
  "records": [
    {
      "userId": 123,
      "name": "Alex",
      "email": "alex@example.com",
      "deletedAt": "2025-10-28 15:30:45"
    },
    {
      "userId": 124,
      "name": "John",
      "email": "john@example.com",
      "deletedAt": "2025-10-27 10:15:20"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

---

## 4. Статистика удаленных записей

### Описание
Получает статистику по всем мягко удаленным записям в системе.

### Запрос
```http
GET /api/soft-delete/statistics
Authorization: Bearer <token>
```

```json
{}
```

### Ответ
```json
{
  "success": true,
  "statistics": {
    "users": 25,
    "stations": 5,
    "powerbanks": 12,
    "orders": 150,
    "total": 192
  }
}
```

---

## 5. Жесткое удаление записи

### Описание
Физически удаляет запись из базы данных. Операция необратима. Требует прав `service_admin`.

### Запрос
```http
DELETE /api/hard-delete/user/123
Authorization: Bearer <token>
```

```json
{
  "confirm": true
}
```

### Ответ
```json
{
  "success": true,
  "message": "Пользователь физически удален из базы данных",
  "userId": 123
}
```

---

## 6. Предпросмотр записей для очистки

### Описание
Показывает список записей, которые будут удалены при очистке (старше указанного количества дней).

### Запрос
```http
GET /api/hard-delete/cleanup/preview?entity_type=user&days_old=90
Authorization: Bearer <token>
```

```json
{}
```

### Ответ
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
      "deletedAt": "2025-05-15 10:20:30"
    },
    {
      "userId": 101,
      "name": "Old User 2",
      "email": "old2@example.com",
      "deletedAt": "2025-05-10 08:15:00"
    }
  ]
}
```

---

## 7. Массовая очистка старых записей

### Описание
Физически удаляет все записи, помеченные как удаленные более N дней назад. Требует прав `service_admin`.

### Запрос
```http
DELETE /api/hard-delete/cleanup
Authorization: Bearer <token>
```

```json
{
  "entityType": "user",
  "daysOld": 90,
  "confirm": true
}
```

### Ответ
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

## 📌 Важно

- **Мягкое удаление** сохраняет данные в БД с флагом `is_deleted = 1`
- **Жесткое удаление** физически удаляет данные из БД навсегда
- Используйте тот же `entity_type` для всех операций (удаление, восстановление, получение списка)

---

## Коды ошибок

### 400 Bad Request
```json
{
  "success": false,
  "error": "Некорректный тип сущности: unknown"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Требуется авторизация"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Недостаточно прав для выполнения операции"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Запись не найдена"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Ошибка сервера: описание ошибки"
}
```

---

## Примеры использования (JavaScript)

### Универсальная функция для любой сущности
```javascript
// Мягкое удаление любой сущности
async function softDelete(entityType, entityId) {
  const response = await fetch(`/api/soft-delete/${entityType}/${entityId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`${entityType} удален:`, data.deletedAt);
  } else {
    console.error('Ошибка:', data.error);
  }
  
  return data;
}

// Примеры использования:
await softDelete('user', 123);        // Удаление пользователя
await softDelete('station', 45);      // Удаление станции
await softDelete('powerbank', 789);   // Удаление повербанка
await softDelete('order', 1001);      // Удаление заказа
```

### Мягкое удаление пользователя
```javascript
async function softDeleteUser(userId) {
  const response = await fetch(`/api/soft-delete/user/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log('Пользователь удален:', data.deletedAt);
  } else {
    console.error('Ошибка:', data.error);
  }
}
```

### Универсальная функция восстановления
```javascript
// Восстановление любой сущности
async function restore(entityType, entityId) {
  const response = await fetch(`/api/soft-delete/restore/${entityType}/${entityId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`${entityType} восстановлен`);
  }
  
  return data;
}

// Примеры:
await restore('user', 123);      // Восстановление пользователя
await restore('station', 45);    // Восстановление станции
await restore('powerbank', 789); // Восстановление повербанка
```

### Универсальная функция получения списка удаленных
```javascript
// Получение списка удаленных записей любой сущности
async function getDeletedRecords(entityType, limit = 10, offset = 0) {
  const response = await fetch(
    `/api/soft-delete/${entityType}?limit=${limit}&offset=${offset}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Удаленные ${entityType}:`, data.records);
    console.log('Всего:', data.total);
  }
  
  return data;
}

// Примеры:
await getDeletedRecords('user', 10, 0);      // Список удаленных пользователей
await getDeletedRecords('station', 20, 0);   // Список удаленных станций
await getDeletedRecords('powerbank', 50, 0); // Список удаленных повербанков
```

### Жесткое удаление
```javascript
async function hardDeleteUser(userId) {
  const response = await fetch(`/api/hard-delete/user/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      confirm: true
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log('Пользователь удален навсегда');
  }
}
```

---

## Важные замечания

1. **Мягкое удаление** - запись остается в БД, можно восстановить
2. **Жесткое удаление** - запись удаляется навсегда, восстановление невозможно
3. Жесткое удаление требует прав **service_admin**
4. Все запросы требуют авторизации
5. При жестком удалении обязательно передавать `"confirm": true`

