# User Favorites API Documentation

API для управления избранными станциями пользователей и их никнеймами.

## Обзор

Система избранных станций позволяет пользователям:
- Добавлять станции в избранное
- Просматривать список избранных станций
- Удалять станции из избранного
- Устанавливать персональные никнеймы для станций
- Удалять никнеймы станций

## Структура данных

### Таблица `user_favorites`
```sql
CREATE TABLE `user_favorites` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `nik` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_fav` (`user_id`,`station_id`),
  KEY `fk_fav_station` (`station_id`)
);
```

## API Endpoints

### 1. Получить избранные станции пользователя

**GET** `/api/user-favorites`

#### Параметры запроса
- `user_id` (обязательный) - ID пользователя

#### Пример запроса
```http
GET /api/user-favorites?user_id=33
```

#### Пример ответа
```json
{
  "success": true,
  "data": [
    {
      "id": 35,
      "user_id": 33,
      "station_id": 13,
      "nik": "Моя любимая станция",
      "created_at": "2025-10-17T08:44:22",
      "station_box_id": "DCHEY02504000019",
      "station_status": "inactive",
      "user_phone": "+79013344076"
    }
  ]
}
```

#### Коды ответов
- `200` - Успешно
- `400` - Не указан user_id
- `500` - Внутренняя ошибка сервера

---

### 2. Добавить станцию в избранное

**POST** `/api/user-favorites`

#### Тело запроса
```json
{
  "user_id": 33,
  "station_id": 13
}
```

#### Пример ответа
```json
{
  "success": true,
  "data": {
    "id": 36
  },
  "message": "Станция добавлена в избранное"
}
```

#### Коды ответов
- `200` - Успешно
- `400` - Отсутствует обязательное поле или станция уже в избранном
- `500` - Внутренняя ошибка сервера

---

### 3. Удалить станцию из избранного

**DELETE** `/api/user-favorites/{favorite_id}`

#### Параметры пути
- `favorite_id` - ID записи в избранном

#### Пример запроса
```http
DELETE /api/user-favorites/35
```

#### Пример ответа
```json
{
  "success": true,
  "message": "Станция удалена из избранного"
}
```

#### Коды ответов
- `200` - Успешно
- `400` - Неверный ID записи
- `404` - Запись в избранном не найдена
- `500` - Внутренняя ошибка сервера

---

### 4. Установить никнейм станции

**PUT** `/api/user-favorites/{favorite_id}/nik`

#### Параметры пути
- `favorite_id` - ID записи в избранном

#### Тело запроса
```json
{
  "nik": "Моя любимая станция"
}
```

#### Пример ответа
```json
{
  "success": true,
  "message": "Никнейм станции установлен",
  "data": {
    "nik": "Моя любимая станция"
  }
}
```

#### Валидация
- Никнейм не может быть пустым
- Максимальная длина: 100 символов
- Пробелы в начале и конце обрезаются

#### Коды ответов
- `200` - Успешно
- `400` - Неверный ID записи или ошибка валидации никнейма
- `404` - Запись в избранном не найдена
- `500` - Внутренняя ошибка сервера

---

### 5. Удалить никнейм станции

**DELETE** `/api/user-favorites/{favorite_id}/nik`

#### Параметры пути
- `favorite_id` - ID записи в избранном

#### Пример запроса
```http
DELETE /api/user-favorites/35/nik
```

#### Пример ответа
```json
{
  "success": true,
  "message": "Никнейм станции удален"
}
```

#### Коды ответов
- `200` - Успешно
- `400` - Неверный ID записи
- `404` - Запись в избранном не найдена
- `500` - Внутренняя ошибка сервера

## Примеры использования

### JavaScript (Fetch API)

```javascript
// Получить избранные станции
async function getUserFavorites(userId) {
  const response = await fetch(`/api/user-favorites?user_id=${userId}`);
  return await response.json();
}

// Добавить станцию в избранное
async function addToFavorites(userId, stationId) {
  const response = await fetch('/api/user-favorites', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      station_id: stationId
    })
  });
  return await response.json();
}

// Установить никнейм станции
async function setStationNik(favoriteId, nik) {
  const response = await fetch(`/api/user-favorites/${favoriteId}/nik`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ nik })
  });
  return await response.json();
}

// Удалить никнейм станции
async function deleteStationNik(favoriteId) {
  const response = await fetch(`/api/user-favorites/${favoriteId}/nik`, {
    method: 'DELETE'
  });
  return await response.json();
}
```

### Python (aiohttp)

```python
import aiohttp
import asyncio

async def get_user_favorites(session, user_id):
    async with session.get(f'/api/user-favorites?user_id={user_id}') as response:
        return await response.json()

async def add_to_favorites(session, user_id, station_id):
    data = {
        'user_id': user_id,
        'station_id': station_id
    }
    async with session.post('/api/user-favorites', json=data) as response:
        return await response.json()

async def set_station_nik(session, favorite_id, nik):
    data = {'nik': nik}
    async with session.put(f'/api/user-favorites/{favorite_id}/nik', json=data) as response:
        return await response.json()

async def delete_station_nik(session, favorite_id):
    async with session.delete(f'/api/user-favorites/{favorite_id}/nik') as response:
        return await response.json()
```

## Ограничения и особенности

1. **Уникальность**: Пользователь не может добавить одну станцию в избранное дважды
2. **Никнеймы**: Каждая запись в избранном может иметь персональный никнейм
3. **Каскадное удаление**: При удалении пользователя или станции, связанные записи в избранном удаляются автоматически
4. **Валидация**: Все входные данные проходят валидацию на сервере

## Интеграция с представлениями

Никнеймы из избранного используются в представлении `v_orders_extended` для отображения пользовательских названий станций:

```sql
SELECT 
  COALESCE(uf.nik, s.box_id) AS station_display_name
FROM orders o
LEFT JOIN station s ON o.station_id = s.station_id
LEFT JOIN user_favorites uf ON (o.user_id = uf.user_id AND o.station_id = uf.station_id)
```

Это позволяет отображать персональные названия станций в истории заказов пользователя.
