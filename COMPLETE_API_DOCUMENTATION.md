# Полная документация API системы управления повербанками

## Содержание
1. [Авторизация и пользователи](#авторизация-и-пользователи)
2. [Административные функции](#административные-функции)
3. [Управление повербанками](#управление-повербанками)
4. [Управление станциями](#управление-станциями)
5. [Управление заказами](#управление-заказами)
6. [Управление группами](#управление-группами)
7. [Выдача повербанков](#выдача-повербанков)
8. [Возврат повербанков](#возврат-повербанков)
9. [Статусы повербанков](#статусы-повербанков)
10.  [Отчеты и мониторинг](#отчеты-и-мониторинг)
11.  [Управление станциями (команды)](#управление-станциями-команды)
12. [Пакетный импорт](#пакетный-импорт)

---

## Авторизация и пользователи

### POST /api/auth/register
Регистрация нового пользователя

**Параметры:**
```json
{
  "fio": "Иван Иванов",
  "phone_e164": "+79001234567",
  "email": "ivan@example.com",
  "password": "password123"
}
```

### POST /api/auth/login
Авторизация пользователя

**Параметры:**
```json
{
  "phone_e164": "+79001234567",
  "password": "password123"
}
```

### GET /api/auth/profile
Получение профиля текущего пользователя

### PUT /api/auth/profile
Обновление профиля пользователя

---

## Административные функции

### GET /api/admin/pending-users
Получение списка пользователей ожидающих одобрения

### POST /api/admin/approve-user
Одобрение пользователя

**Параметры:**
```json
{
  "user_id": 123,
  "role": "user",
  "org_unit_id": 1
}
```

### POST /api/admin/reject-user
Отклонение пользователя

**Параметры:**
```json
{
  "user_id": 123,
  "reason": "Неверные данные"
}
```

### POST /api/admin/reset-email
Сброс email сервиса

### GET /api/admin/unknown-powerbanks
Получение списка повербанков со статусом unknown

### POST /api/admin/activate-powerbank
Активация повербанка

**Параметры:**
```json
{
  "powerbank_id": 123,
  "admin_user_id": 1,
  "target_org_unit_id": 1
}
```

### POST /api/admin/deactivate-powerbank
Деактивация повербанка

**Параметры:**
```json
{
  "powerbank_id": 123,
  "admin_user_id": 1,
  "reason": "admin_deactivated"
}
```

### GET /api/admin/powerbank-status/{powerbank_id}
Получение статуса повербанка

### POST /api/admin/bulk-activate-powerbanks
Массовая активация повербанков

**Параметры:**
```json
{
  "powerbank_ids": [123, 124, 125],
  "admin_user_id": 1,
  "target_org_unit_id": 1
}
```

### GET /api/admin/powerbank-statistics
Получение статистики по повербанкам

### POST /api/admin/force-eject-powerbank
Принудительное извлечение повербанка

**Параметры:**
```json
{
  "station_id": 13,
  "slot_number": 1,
  "admin_user_id": 1
}
```

### POST /api/admin/write-off-powerbank
Списание повербанка как утерянного

**Параметры:**
```json
{
  "user_id": 33,
  "powerbank_id": 53,
  "admin_user_id": 18,
  "note": "Lost by user"
}
```

---

## Управление повербанками

### POST /api/powerbanks
Создание повербанка

**Параметры:**
```json
{
  "serial_number": "PB001",
  "org_unit_id": 1,
  "soh": 100,
  "status": "unknown",
  "write_off_reason": "none"
}
```

### GET /api/powerbanks
Получение списка повербанков

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `status` (string) - фильтр по статусу
- `org_unit_id` (int) - фильтр по группе

### GET /api/powerbanks/{powerbank_id}
Получение повербанка по ID

### PUT /api/powerbanks/{powerbank_id}
Обновление повербанка

### PUT /api/powerbanks/{powerbank_id}/approve
Одобрение повербанка

**Параметры:**
```json
{
  "org_unit_id": 1,
  "soh": 100
}
```

### DELETE /api/powerbanks/{powerbank_id}
Удаление повербанка

---

## Управление станциями

### POST /api/stations
Создание станции

**Параметры:**
```json
{
  "org_unit_id": 1,
  "box_id": "ST001",
  "iccid": "123456789",
  "slots_declared": 8,
  "status": "active"
}
```

### GET /api/stations
Получение списка станций

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `org_unit_id` (int) - фильтр по группе
- `status` (string) - фильтр по статусу

### GET /api/stations/{station_id}
Получение станции по ID

### PUT /api/stations/{station_id}
Обновление станции

### DELETE /api/stations/{station_id}
Удаление станции

---

## Управление заказами

### POST /api/orders
Создание заказа

**Параметры:**
```json
{
  "station_id": 13,
  "user_id": 33,
  "powerbank_id": 53,
  "status": "borrow"
}
```

### GET /api/orders
Получение списка заказов

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `user_id` (int) - фильтр по пользователю
- `station_id` (int) - фильтр по станции
- `status` (string) - фильтр по статусу

### GET /api/orders/{order_id}
Получение заказа по ID

### PUT /api/orders/{order_id}
Обновление заказа

### DELETE /api/orders/{order_id}
Удаление заказа

---

## Управление группами

### POST /api/org-units
Создание организационной единицы

**Параметры:**
```json
{
  "parent_org_unit_id": null,
  "unit_type": "group",
  "name": "Отдел продаж",
  "adress": "Москва, ул. Примерная, 1",
  "logo_url": "https://example.com/logo.png",
  "default_powerbank_limit": 3,
  "reminder_hours": 24
}
```

### GET /api/org-units
Получение списка организационных единиц

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `unit_type` (string) - фильтр по типу
- `parent_id` (int) - фильтр по родительской группе

### GET /api/org-units/{org_unit_id}
Получение организационной единицы по ID

### PUT /api/org-units/{org_unit_id}
Обновление организационной единицы

### DELETE /api/org-units/{org_unit_id}
Удаление организационной единицы

---

## Управление пользователями

### POST /api/users
Создание пользователя

**Параметры:**
```json
{
  "fio": "Иван Иванов",
  "phone_e164": "+79001234567",
  "email": "ivan@example.com",
  "role": "user",
  "status": "active",
  "password": "password123",
  "powerbank_limit": 2
}
```

### GET /api/users
Получение списка пользователей

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `status` (string) - фильтр по статусу
- `role` (string) - фильтр по роли

### GET /api/users/{user_id}
Получение пользователя по ID

### PUT /api/users/{user_id}
Обновление пользователя

**Параметры:**
```json
{
  "fio": "Иван Иванов",
  "phone_e164": "+79001234567",
  "email": "ivan@example.com",
  "status": "active",
  "powerbank_limit": 3,
  "role": "user",
  "parent_org_unit_id": 1
}
```

### DELETE /api/users/{user_id}
Удаление пользователя

---

## Выдача повербанков

### GET /api/borrow/stations/{station_id}/powerbanks
Получение доступных повербанков на станции

### GET /api/borrow/stations/{station_id}/slots/{slot_number}/status
Получение статуса слота

### POST /api/borrow/stations/{station_id}/request
Запрос выдачи повербанка

**Параметры:**
```json
{
  "user_id": 33,
  "slot_number": 1
}
```

### GET /api/borrow/stations/{station_id}/info
Получение информации о станции

### GET /api/borrow/stations/{station_id}/select-optimal
Выбор оптимального повербанка

### POST /api/borrow/stations/{station_id}/request-optimal
Запрос выдачи оптимального повербанка

**Параметры:**
```json
{
  "user_id": 33
}
```

### POST /api/borrow/powerbanks/{powerbank_id}/request
Запрос выдачи конкретного повербанка

**Параметры:**
```json
{
  "user_id": 33
}
```

---

## Возврат повербанков

### POST /api/return-powerbank
Запуск процесса возврата повербанка. Возвращает мгновенный ответ о старте процесса (а не подтверждение факта возврата).

**Параметры:**
```json
{
  "station_id": 13,
  "user_id": 33,
  "powerbank_id": 53
}
```

**Ответ (успех):**
```json
{
  "success": true,
  "message": "Процесс возврата запущен. Вставьте повербанк в станцию в течение 10 секунд.",
  "powerbank_id": 53,
  "serial_number": "4443484154000016",
  "station_id": 13,
  "timestamp": "2025-10-16T10:00:00+03:00"
}
```

---

### POST /api/return/wait-confirmation
Ожидание подтверждения, что повербанк действительно появился в станции (подтверждение возврата).

Таймаут ожидания задаётся ТОЛЬКО на сервере (см. `config/settings.py` → `RETURN_CONFIRMATION_TIMEOUT_SECONDS`, по умолчанию 10 секунд). Клиент не должен и не может переопределять таймаут.

**Параметры:**
```json
{
  "station_id": 13,
  "user_id": 33,
  "powerbank_id": 53,        // необязательное
  "message": "опционально"   // необязательное
}
```

**Ответ (подтверждение найдено до тайм-аута):**
```json
{
  "success": true,
  "station_id": 13,
  "user_id": 33,
  "confirmed": true,
  "powerbank_id": 53,
  "slot_number": 7,
  "timeout": false
}
```

**Ответ (истёк тайм-аут ожидания, HTTP 408):**
```json
{
  "success": false,
  "station_id": 13,
  "user_id": 33,
  "confirmed": false,
  "timeout": true,
  "error": "Не удалось подтвердить возврат в отведенное время"
}
```

---

### GET /api/return/stations/{station_id}/active-orders
Список активных заказов со статусом выдачи/возврата для указанной станции.

**Ответ:**
```json
{
  "success": true,
  "orders": [
    {
      "order_id": 987,
      "station_id": 13,
      "user_id": 33,
      "powerbank_id": 53,
      "status": "borrow",
      "timestamp": "2025-10-16T09:58:00+03:00"
    }
  ],
  "count": 1
}
```

### POST /powerbank-error-report
Отчет об ошибке повербанка

**Параметры:**
```json
{
  "order_id": 123,                 // обязателен
  "powerbank_id": 53,              // обязателен
  "station_id": 13,                // обязателен
  "user_id": 33,                   // обязателен
  "error_type": "broken",         // обязателен
  "additional_notes": "..."       // необязателен
}
```

---

## Статусы повербанков

### GET /api/powerbanks-status
Получение повербанков со статусами

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `status_filter` (string) - фильтр по статусу
- `org_unit_id` (int) - фильтр по группе

### GET /api/powerbanks-status/summary
Получение сводки по статусам

### GET /api/powerbanks-status/{powerbank_id}
Получение статуса конкретного повербанка

### GET /api/powerbanks/status
Алиас для /api/powerbanks-status

### GET /api/powerbanks/status/summary
Алиас для /api/powerbanks-status/summary

### GET /api/powerbanks/{powerbank_id}/status
Алиас для /api/powerbanks-status/{powerbank_id}

---

## Отчеты и мониторинг

### POST /api/slot-abnormal-reports
Создание отчета об аномалии слота

**Параметры:**
```json
{
  "station_id": 13,
  "slot_number": 1,
  "terminal_id": "4443484154000016",
  "event_type": "1",
  "reported_at": "2025-10-12T10:00:00Z"
}
```

### GET /api/slot-abnormal-reports
Получение отчетов об аномалиях

**Параметры запроса:**
- `page` (int) - номер страницы
- `limit` (int) - количество на странице
- `station_id` (int) - фильтр по станции
- `event_type` (string) - фильтр по типу события

### GET /api/slot-abnormal-reports/{report_id}
Получение отчета по ID

### DELETE /api/slot-abnormal-reports/{report_id}
Удаление отчета

---

## Управление станциями (команды)

### POST /api/restart-cabinet
Перезагрузка кабинета

**Параметры:**
```json
{
  "station_id": 13
}
```

### POST /api/query-inventory
Запрос инвентаря

**Параметры:**
```json
{
  "station_id": 13
}
```

### GET /api/query-inventory/station/{station_id}
Получение инвентаря станции

### POST /api/query-voice-volume
Запрос уровня громкости

**Параметры:**
```json
{
  "station_id": 13
}
```

### GET /api/query-voice-volume/station/{station_id}
Получение данных о громкости

### POST /api/set-voice-volume
Установка уровня громкости

**Параметры:**
```json
{
  "station_id": 13,
  "volume": 50
}
```

### POST /api/set-server-address
Установка адреса сервера

**Параметры:**
```json
{
  "station_id": 13,
  "server_address": "192.168.1.100"
}
```

### POST /api/query-server-address
Запрос адреса сервера

**Параметры:**
```json
{
  "station_id": 13
}
```

### GET /api/query-server-address/station/{station_id}
Получение данных об адресе сервера

### GET /api/iccid/stations/{station_id}
Получение ICCID станции

---

## Пакетный импорт

### POST /api/users/bulk-import
Пакетный импорт пользователей из Excel

**Параметры (multipart/form-data):**
- `file` - Excel файл с пользователями

### GET /api/users/bulk-import/template
Получение шаблона Excel файла

### POST /api/users/bulk-import/validate
Валидация Excel файла

**Параметры (multipart/form-data):**
- `file` - Excel файл для валидации

---

## Дополнительные API

### POST /api/user-roles
Создание роли пользователя

### GET /api/user-roles
Получение ролей пользователей

### DELETE /api/user-roles/{role_id}
Удаление роли

### POST /api/user-favorites
Добавление станции в избранное

### GET /api/user-favorites
Получение избранных станций

### DELETE /api/user-favorites/{favorite_id}
Удаление из избранного

### POST /api/station-powerbanks
Создание связи станция-повербанк

### GET /api/station-powerbanks
Получение связей станция-повербанк

### DELETE /api/station-powerbanks/{sp_id}
Удаление связи

### POST /api/station-secret-keys
Создание секретного ключа станции

### GET /api/station-secret-keys
Получение секретных ключей

### DELETE /api/station-secret-keys/{key_id}
Удаление секретного ключа

### DELETE /api/station-secret-keys
Удаление ключей по станции

---

## Пользовательские API

### GET /api/user/powerbanks/available
Получение доступных повербанков для пользователя

### GET /api/user/orders
Получение заказов пользователя

### POST /api/user/powerbanks/borrow
Выдача повербанка пользователю

### POST /api/user/powerbanks/return
Возврат повербанка пользователем

### POST /api/return-damage
Возврат с поломкой

### GET /api/user/stations
Получение станций доступных пользователю

### GET /api/user/profile
Получение профиля пользователя

---

## Коды ответов

- `200` - Успешный запрос
- `201` - Ресурс создан
- `400` - Неверные параметры запроса
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Ресурс не найден
- `408` - Таймаут операции
- `500` - Внутренняя ошибка сервера

## Формат ответов

**Успешный ответ:**
```json
{
  "success": true,
  "data": {...},
  "message": "Операция выполнена успешно"
}
```

**Ответ с ошибкой:**
```json
{
  "success": false,
  "error": "Описание ошибки"
}
```

**Ответ с пагинацией:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  }
}
```
