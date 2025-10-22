# Backend API Documentation

## Содержание

Документация содержит **114 основных API endpoints** (+ 3 алиаса для обратной совместимости):

- **Authentication & User Management** - регистрация, вход, профиль (4 endpoints)
- **Admin Functions** - управление пользователями, email (4 endpoints)
- **Powerbank Management** - CRUD операции с аккумуляторами (7 endpoints)
- **Powerbank Status API** - статусы аккумуляторов (3 endpoints)
- **Admin Powerbank Operations** - административные операции (8 endpoints)
- **User Management** - управление пользователями (5 endpoints)
- **Station Management** - управление станциями (6 endpoints)
- **Order Management** - управление заказами (6 endpoints)
- **Organization Units** - организационные единицы (5 endpoints)
- **User Powerbank Operations** - операции пользователя с аккумуляторами (10 endpoints)
- **Borrow Operations** - выдача аккумуляторов (7 endpoints)
- **Return Operations** - возврат с ошибкой (5 endpoints)
- **Station Control Commands** - управление станциями (8 endpoints)
- **Bulk Import** - массовый импорт (3 endpoints)
- **Other Entities** - роли, избранное, связи, ключи (13 endpoints)
- **Invitations** - приглашения (4 endpoints)
- **Invitations Storage** - хранилище приглашений без БД (3 endpoints)
- **Logo Management** - управление логотипами (4 endpoints)
- **Error Reports** - отчеты об аномалиях слотов (6 endpoints)

---

## Authentication & User Management

### POST /api/auth/register
Регистрация пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Пользователь зарегистрирован",
  "user_id": 123,
  "token": "jwt_token"
}
```

### POST /api/auth/login
Вход пользователя
**Success (200):**
```json
{
  "success": true,
  "token": "jwt_token",
  "user": {
    "user_id": 123,
    "role": "user"
  }
}
```

### GET /api/auth/profile
Получение профиля пользователя
**Success (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "phone": "+70000000000",
    "email": "user@example.com"
  }
}
```

### PUT /api/auth/profile
Обновление профиля пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Профиль обновлен"
}
```

## Admin Functions

### GET /api/admin/pending-users
Получение списка пользователей на утверждении
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "user_id": 123,
      "phone": "+70000000000"
    }
  ]
}
```

### POST /api/admin/approve-user
Утверждение пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Пользователь утвержден"
}
```

### POST /api/admin/reject-user
Отклонение пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Пользователь отклонен"
}
```

### POST /api/admin/reset-email
Сброс состояния email сервиса
**Success (200):**
```json
{
  "success": true,
  "message": "Email сервис сброшен"
}
```

## Powerbank Management

### POST /api/powerbanks
Создание аккумулятора
**Success (200):**
```json
{
  "success": true,
  "data": {"id": 123},
  "message": "Аккумулятор создан"
}
```
**Error (400):**
```json
{
  "success": false,
  "error": "Отсутствует обязательное поле: serial_number"
}
```

### GET /api/powerbanks
Получение списка аккумуляторов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "serial_number": "PB-12345",
      "status": "active"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100
  }
}
```

### GET /api/powerbanks/{powerbank_id}
Получение аккумулятора по ID
**Success (200):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "serial_number": "PB-12345",
    "status": "active"
  }
}
```
**Error (404):**
```json
{
  "success": false,
  "error": "Аккумулятор не найден"
}
```

### PUT /api/powerbanks/{powerbank_id}
Обновление аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор обновлен"
}
```

### PUT /api/powerbanks/{powerbank_id}/approve
Утверждение аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор утвержден"
}
```

### POST /api/powerbanks/{powerbank_id}/reset-error
Сброс ошибки аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Ошибка повербанка успешно сброшена",
  "powerbank_id": 123,
  "serial_number": "PB-12345"
}
```
**Error (404):**
```json
{
  "success": false,
  "error": "Аккумулятор не найден"
}
```

### DELETE /api/powerbanks/{powerbank_id}
Удаление аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор удален"
}
```

## Powerbank Status API

### GET /api/powerbanks-status
Получение аккумуляторов со статусами
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "serial_number": "PB-12345",
      "status": "active"
    }
  ]
}
```
**Алиас:** GET /api/powerbanks/status

### GET /api/powerbanks-status/summary
Сводка по статусам аккумуляторов
**Success (200):**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "active": 80,
    "unknown": 10,
    "broken": 5,
    "system_error": 3,
    "written_off": 2
  }
}
```
**Алиас:** GET /api/powerbanks/status/summary

### GET /api/powerbanks-status/{powerbank_id}
Статус конкретного аккумулятора
**Success (200):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "serial_number": "PB-12345",
    "status": "active"
  }
}
```
**Алиас:** GET /api/powerbanks/{powerbank_id}/status

## Admin Powerbank Operations

### GET /api/admin/unknown-powerbanks
Получение неизвестных аккумуляторов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "serial_number": "PB-12345"
    }
  ]
}
```

### POST /api/admin/activate-powerbank
Активация аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Повербанк активирован",
  "powerbank_id": 123
}
```

### POST /api/admin/deactivate-powerbank
Деактивация аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Повербанк деактивирован",
  "powerbank_id": 123
}
```

### POST /api/admin/bulk-activate-powerbanks
Массовая активация аккумуляторов
**Success (200):**
```json
{
  "success": true,
  "message": "Обработано 10 повербанков",
  "success_count": 8,
  "error_count": 2
}
```

### GET /api/admin/powerbank-statistics
Статистика по аккумуляторам
**Success (200):**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "active": 80,
    "unknown": 10,
    "group_statistics": []
  }
}
```

### POST /api/admin/force-eject-powerbank
Принудительное извлечение аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Повербанк принудительно извлечен",
  "station_id": 1,
  "slot_number": 5
}
```

### POST /api/admin/write-off-powerbank
Списание аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Повербанк списан",
  "powerbank_id": 123
}
```

## User Management

### POST /api/users
Создание пользователя
**Success (200):**
```json
{
  "success": true,
  "data": {"user_id": 123},
  "message": "Пользователь создан"
}
```

### GET /api/users
Получение списка пользователей
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "user_id": 123,
      "phone": "+70000000000"
    }
  ]
}
```

### GET /api/users/{user_id}
Получение пользователя по ID
**Success (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "phone": "+70000000000",
    "role": "user"
  }
}
```

### PUT /api/users/{user_id}
Обновление пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Пользователь обновлен"
}
```

### DELETE /api/users/{user_id}
Удаление пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Пользователь удален"
}
```

## Station Management

### POST /api/stations
Создание станции
**Success (200):**
```json
{
  "success": true,
  "data": {"station_id": 123},
  "message": "Станция создана"
}
```

### GET /api/stations
Получение списка станций
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "station_id": 123,
      "box_id": "ST-001"
    }
  ]
}
```

### GET /api/stations/{station_id}
Получение станции по ID
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "box_id": "ST-001"
  }
}
```

### PUT /api/stations/{station_id}
Обновление станции
**Success (200):**
```json
{
  "success": true,
  "message": "Станция обновлена"
}
```

### PUT /api/stations/{station_id}/nik
Обновление NIK станции
**Success (200):**
```json
{
  "success": true,
  "message": "NIK станции обновлен"
}
```

### DELETE /api/stations/{station_id}
Удаление станции
**Success (200):**
```json
{
  "success": true,
  "message": "Станция удалена"
}
```

## Order Management

### POST /api/orders
Создание заказа
**Success (200):**
```json
{
  "success": true,
  "data": {"order_id": 123},
  "message": "Заказ создан"
}
```

### GET /api/orders
Получение списка заказов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 123,
      "user_id": 456
    }
  ]
}
```

### GET /api/orders/extended
Расширенный список заказов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 123,
      "user_id": 456,
      "status": "active"
    }
  ]
}
```

### GET /api/orders/{order_id}
Получение заказа по ID
**Success (200):**
```json
{
  "success": true,
  "data": {
    "order_id": 123,
    "status": "active"
  }
}
```

### PUT /api/orders/{order_id}
Обновление заказа
**Success (200):**
```json
{
  "success": true,
  "message": "Заказ обновлен"
}
```

### DELETE /api/orders/{order_id}
Удаление заказа
**Success (200):**
```json
{
  "success": true,
  "message": "Заказ удален"
}
```

## Organization Units

### POST /api/org-units
Создание организационной единицы
**Success (200):**
```json
{
  "success": true,
  "data": {"org_unit_id": 123},
  "message": "Организационная единица создана"
}
```

### GET /api/org-units
Получение списка организационных единиц
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "org_unit_id": 123,
      "name": "Office 1"
    }
  ]
}
```

### GET /api/org-units/{org_unit_id}
Получение организационной единицы по ID
**Success (200):**
```json
{
  "success": true,
  "data": {
    "org_unit_id": 123,
    "name": "Office 1"
  }
}
```

### PUT /api/org-units/{org_unit_id}
Обновление организационной единицы
**Success (200):**
```json
{
  "success": true,
  "message": "Организационная единица обновлена"
}
```

### DELETE /api/org-units/{org_unit_id}
Удаление организационной единицы
**Success (200):**
```json
{
  "success": true,
  "message": "Организационная единица удалена"
}
```

## User Powerbank Operations

### GET /api/user/powerbanks/available
Доступные аккумуляторы для пользователя
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "serial_number": "PB-12345"
    }
  ]
}
```

### GET /api/user/orders
Заказы пользователя (SSE)
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 123,
      "status": "active"
    }
  ]
}
```

### POST /api/user/powerbanks/borrow
Взять аккумулятор
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор выдан",
  "order_id": 123
}
```

### POST /api/user/powerbanks/return
Вернуть аккумулятор
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор возвращен"
}
```

### POST /api/return-damage
Вернуть поврежденный аккумулятор
**Success (200):**
```json
{
  "success": true,
  "message": "Поврежденный аккумулятор возвращен"
}
```

### POST /api/return-error
Вернуть аккумулятор с ошибкой
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор с ошибкой возвращен"
}
```

### GET /api/powerbank-error-types
Типы ошибок аккумуляторов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "type_error": "Battery low"
    }
  ]
}
```

### GET /api/user/stations
Станции для пользователя
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "station_id": 123,
      "box_id": "ST-001"
    }
  ]
}
```

### GET /api/user/stations/availability
Доступность слотов с лимитами
**Success (200):**
```json
{
  "success": true,
  "data": {
    "available_slots": 5,
    "user_limit": 2
  }
}
```

### GET /api/user/profile
Профиль пользователя
**Success (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "phone": "+70000000000"
  }
}
```

## Borrow Operations

### GET /api/borrow/stations/{station_id}/powerbanks
Доступные аккумуляторы на станции
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "powerbank_id": 123,
      "serial_number": "PB-12345"
    }
  ]
}
```

### GET /api/borrow/stations/{station_id}/slots/{slot_number}/status
Статус слота станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "slot_number": 1,
    "status": "occupied"
  }
}
```

### POST /api/borrow/stations/{station_id}/request
Запрос на выдачу аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос отправлен"
}
```

### GET /api/borrow/stations/{station_id}/info
Информация о станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "slots_total": 10,
    "slots_occupied": 3
  }
}
```

### GET /api/borrow/stations/{station_id}/select-optimal
Выбор оптимального аккумулятора
**Success (200):**
```json
{
  "success": true,
  "data": {
    "powerbank_id": 123,
    "soh": 85
  }
}
```

### POST /api/borrow/stations/{station_id}/request-optimal
Запрос на оптимальный аккумулятор
**Success (200):**
```json
{
  "success": true,
  "message": "Оптимальный аккумулятор запрошен"
}
```

### POST /api/borrow/powerbanks/{powerbank_id}/request
Запрос конкретного аккумулятора
**Success (200):**
```json
{
  "success": true,
  "message": "Аккумулятор запрошен"
}
```

## Return Operations

### POST /api/return/error
Запрос на возврат с ошибкой
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос на возврат с ошибкой создан"
}
```

### GET /api/return/error/pending
Ожидающие возвраты с ошибкой
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "request_id": 123,
      "user_id": 456
    }
  ]
}
```

### DELETE /api/return/error/pending/{user_id}
Отмена запроса на возврат с ошибкой
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос отменен"
}
```

### GET /api/return/error/types
Типы ошибок для возврата
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Battery damaged"
    }
  ]
}
```

### POST /api/return/error/cleanup
Очистка просроченных запросов
**Success (200):**
```json
{
  "success": true,
  "message": "Очистка завершена"
}
```

## Station Control Commands

### POST /api/restart-cabinet
Перезагрузка станции
**Success (200):**
```json
{
  "success": true,
  "message": "Команда перезагрузки отправлена",
  "station_box_id": "ST-001"
}
```

### GET /api/station-status/{station_id}
Статус станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "status": "active",
    "last_seen": "2025-01-01T12:00:00"
  }
}
```

### POST /api/query-inventory
Запрос инвентаря станции
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос инвентаря отправлен"
}
```

### GET /api/query-inventory/station/{station_id}
Инвентарь конкретной станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "slots": [
      {
        "slot_number": 1,
        "powerbank_id": 456
      }
    ]
  }
}
```

### POST /api/query-voice-volume
Запрос уровня громкости
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос уровня громкости отправлен"
}
```

### GET /api/query-voice-volume/station/{station_id}
Уровень громкости станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "voice_volume": 50
  }
}
```

### POST /api/set-voice-volume
Установка уровня громкости
**Success (200):**
```json
{
  "success": true,
  "message": "Уровень громкости установлен"
}
```

### POST /api/set-server-address
Установка адреса сервера
**Success (200):**
```json
{
  "success": true,
  "message": "Адрес сервера установлен"
}
```

### POST /api/query-server-address
Запрос адреса сервера
**Success (200):**
```json
{
  "success": true,
  "message": "Запрос адреса сервера отправлен"
}
```

### GET /api/query-server-address/station/{station_id}
Адрес сервера для станции
**Success (200):**
```json
{
  "success": true,
  "data": {
    "station_id": 123,
    "server_address": "192.168.1.100"
  }
}
```

## Bulk Import

### POST /api/users/bulk-import
Массовый импорт пользователей
**Success (200):**
```json
{
  "success": true,
  "message": "Импорт завершен",
  "imported": 100,
  "errors": 5
}
```

### GET /api/users/bulk-import/template
Шаблон для импорта
**Success (200):**
```json
{
  "success": true,
  "data": {
    "columns": ["phone", "fio", "email"]
  }
}
```

### POST /api/users/bulk-import/validate
Валидация файла импорта
**Success (200):**
```json
{
  "success": true,
  "valid_rows": 95,
  "invalid_rows": 5,
  "errors": []
}
```

## Other Entities

### POST /api/user-roles
Создание роли пользователя
**Success (200):**
```json
{
  "success": true,
  "data": {"role_id": 123}
}
```

### GET /api/user-roles
Получение ролей пользователей
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "role_id": 123,
      "name": "admin"
    }
  ]
}
```

### DELETE /api/user-roles/{role_id}
Удаление роли пользователя
**Success (200):**
```json
{
  "success": true,
  "message": "Роль удалена"
}
```

### POST /api/user-favorites
Создание избранного пользователя
**Success (200):**
```json
{
  "success": true,
  "data": {"favorite_id": 123}
}
```

### GET /api/user-favorites
Избранное пользователя
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "favorite_id": 123,
      "station_id": 456
    }
  ]
}
```

### DELETE /api/user-favorites/{favorite_id}
Удаление избранного
**Success (200):**
```json
{
  "success": true,
  "message": "Избранное удалено"
}
```

### PUT /api/user-favorites/{favorite_id}/nik
Установка NIK для избранного
**Success (200):**
```json
{
  "success": true,
  "message": "NIK установлен"
}
```

### DELETE /api/user-favorites/{favorite_id}/nik
Удаление NIK для избранного
**Success (200):**
```json
{
  "success": true,
  "message": "NIK удален"
}
```

### POST /api/station-powerbanks
Создание связи станция-аккумулятор
**Success (200):**
```json
{
  "success": true,
  "data": {"sp_id": 123}
}
```

### GET /api/station-powerbanks
Связи станция-аккумулятор
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "sp_id": 123,
      "station_id": 456,
      "powerbank_id": 789
    }
  ]
}
```

### DELETE /api/station-powerbanks/{sp_id}
Удаление связи станция-аккумулятор
**Success (200):**
```json
{
  "success": true,
  "message": "Связь удалена"
}
```

### POST /api/station-secret-keys
Создание секретного ключа станции
**Success (200):**
```json
{
  "success": true,
  "data": {"key_id": 123}
}
```

### GET /api/station-secret-keys
Получение секретных ключей станций
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "key_id": 123,
      "station_id": 456,
      "secret_key": "key123"
    }
  ]
}
```

### DELETE /api/station-secret-keys/{key_id}
Удаление секретного ключа по ID
**Success (200):**
```json
{
  "success": true,
  "message": "Секретный ключ удален"
}
```

### DELETE /api/station-secret-keys
Удаление секретного ключа по станции
**Success (200):**
```json
{
  "success": true,
  "message": "Секретный ключ станции удален"
}
```

## Invitations

### POST /api/invitations/generate
Генерация ссылки приглашения
**Success (200):**
```json
{
  "success": true,
  "invitation_link": "https://example.com/invite/abc123"
}
```

### GET /api/invitations/{token}
Информация о приглашении
**Success (200):**
```json
{
  "success": true,
  "data": {
    "org_unit_id": 123,
    "expires_at": "2025-01-01T12:00:00"
  }
}
```

### POST /api/invitations/register
Регистрация по приглашению
**Success (200):**
```json
{
  "success": true,
  "message": "Регистрация завершена",
  "user_id": 123
}
```

### GET /api/invitations
Список приглашений
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "token": "abc123",
      "org_unit_id": 456
    }
  ]
}
```

## Invitations Storage (без БД)

### POST /api/invitations/storage/store
Сохранение приглашения в JSON-файл
**Success (200):**
```json
{
  "success": true,
  "message": "Приглашение сохранено",
  "token": "abc123"
}
```

### GET /api/invitations/storage/{token}
Получение приглашения из JSON-файла
**Success (200):**
```json
{
  "success": true,
  "data": {
    "token": "abc123",
    "org_unit_id": 456
  }
}
```

### GET /api/invitations/storage/statistics
Статистика хранилища приглашений
**Success (200):**
```json
{
  "success": true,
  "data": {
    "total": 10,
    "active": 5,
    "expired": 5
  }
}
```

## Logo Management

### POST /api/org-units/{org_unit_id}/logo
Загрузка логотипа
**Success (200):**
```json
{
  "success": true,
  "message": "Логотип загружен",
  "filename": "logo_123.png"
}
```

### POST /api/org-units/{org_unit_id}/logo-url
Загрузка логотипа по URL
**Success (200):**
```json
{
  "success": true,
  "message": "Логотип загружен по URL"
}
```

### DELETE /api/org-units/{org_unit_id}/logo
Удаление логотипа
**Success (200):**
```json
{
  "success": true,
  "message": "Логотип удален"
}
```

### GET /api/logos/{filename}
Получение логотипа
**Success (200):**
```json
{
  "success": true,
  "data": "base64_image_data"
}
```

## Error Reports

### GET /api/slot-abnormal-reports
Отчеты об аномалиях слотов
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "report_id": 123,
      "station_id": 456,
      "event_type": "slot_error"
    }
  ]
}
```

### GET /api/slot-abnormal-reports/stations/{station_id}
Отчеты об аномалиях для станции
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "report_id": 123,
      "event_type": "slot_error"
    }
  ]
}
```

### GET /api/slot-abnormal-reports/statistics
Статистика аномалий
**Success (200):**
```json
{
  "success": true,
  "data": {
    "total_reports": 100,
    "error_types": {
      "slot_error": 50,
      "communication_error": 30
    }
  }
}
```

### GET /api/slot-abnormal-reports/event-type/{event_type}
Отчеты по типу события
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "report_id": 123,
      "station_id": 456
    }
  ]
}
```

### GET /api/slot-abnormal-reports/date-range
Отчеты за период
**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "report_id": 123,
      "created_at": "2025-01-01T12:00:00"
    }
  ]
}
```

### DELETE /api/slot-abnormal-reports/{report_id}
Удаление отчета об аномалии
**Success (200):**
```json
{
  "success": true,
  "message": "Отчет удален"
}
```

## Common Error Responses

**Error (400):**
```json
{
  "success": false,
  "error": "Неверные параметры запроса"
}
```

**Error (401):**
```json
{
  "success": false,
  "error": "Неавторизован"
}
```

**Error (403):**
```json
{
  "success": false,
  "error": "Недостаточно прав"
}
```

**Error (404):**
```json
{
  "success": false,
  "error": "Ресурс не найден"
}
```

**Error (500):**
```json
{
  "success": false,
  "error": "Внутренняя ошибка сервера"
}
```

