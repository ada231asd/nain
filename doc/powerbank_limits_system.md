# Система лимитов повербанков

## Описание

Система контролирует количество повербанков, которое пользователь может взять одновременно. Лимиты не применяются к администраторам.

## Приоритет лимитов

1. **Индивидуальный лимит** (`powerbank_limit` в таблице `app_user`) - наивысший приоритет
2. **Групповой лимит** (`default_powerbank_limit` в таблице `org_unit`) - если индивидуальный не задан
3. **Администраторы** (`service_admin`, `group_admin`, `subgroup_admin`) - лимиты не применяются

## Логика расчета доступного количества

**Для обычных пользователей:**
```
доступно_к_взятию = min(свободно_в_станции, лимит - уже_взято)
```

**Для админов:**
```
доступно_к_взятию = свободно_в_станции
```

## API Endpoint

**GET** `/api/user/stations/availability`

### Response

```json
{
  "success": true,
  "data": {
    "stations": [
      {
        "station_id": 13,
        "box_id": "DCHEY02504000019",
        "slots_declared": 8,
        "remain_num": 3,
        "available_powerbanks": 3,
        "user_available_slots": 2,
        "status": "active",
        "last_seen": "2025-10-22T17:00:00Z",
        "access_reason": "Доступ разрешен"
      }
    ],
    "total_available_slots": 2,
    "user_limits": {
      "max_limit": 2,
      "current_borrowed": 0,
      "available_by_limit": 2
    }
  }
}
```

### Поля user_limits

- `max_limit`: Максимальный лимит пользователя (число или "unlimited" для админов)
- `current_borrowed`: Сколько повербанков уже взято
- `available_by_limit`: Сколько еще можно взять по лимиту (число или "unlimited")

### Поля станции

- `available_powerbanks`: Свободных повербанков в станции
- `user_available_slots`: Доступно для взятия пользователем с учетом лимита

## Frontend отображение

**Карточка станции:**
```
можно взять: {min(freePorts, available_by_limit)}
в станции: {freePorts}/{totalPorts}
```

Где:
- `freePorts` - свободных повербанков в станции
- `totalPorts` - всего слотов в станции
- `available_by_limit` - доступно по лимиту пользователя

## Обновление лимитов

Лимиты автоматически обновляются:
- При логине пользователя
- При загрузке Dashboard
- После взятия повербанка
- После возврата повербанка

## Хранение на Frontend

**Store:** `authStore.userLimits`

```json
{
  "max_limit": 2,
  "current_borrowed": 0,
  "available_by_limit": 2
}
```

**Getter:** `authStore.availableByLimit` - возвращает `user_limits.available_by_limit`

