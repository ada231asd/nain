# API для работы с избранными станциями пользователей

## Обзор

API для работы с избранными станциями позволяет пользователям добавлять станции в избранное, просматривать список избранных станций и удалять станции из избранного.

## Эндпоинты

### 1. Добавить станцию в избранное
**POST** `/api/user-favorites`

**Параметры:**
- `user_id` (int, обязательный) - ID пользователя
- `station_id` (int, обязательный) - ID станции

**Пример запроса:**
```bash
curl -X POST http://localhost:8080/api/user-favorites \
  -H "Content-Type: application/json" \
  -d '{"user_id": 8, "station_id": 1}'
```

**Пример ответа:**
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "Станция добавлена в избранное"
}
```

### 2. Получить избранные станции пользователя
**GET** `/api/user-favorites?user_id={user_id}`

**Параметры:**
- `user_id` (int, обязательный) - ID пользователя

**Пример запроса:**
```bash
curl "http://localhost:8080/api/user-favorites?user_id=8"
```

**Пример ответа:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 8,
      "station_id": 1,
      "created_at": "2025-09-22T10:30:00",
      "station_box_id": "STATION_001",
      "station_status": "active",
      "user_phone": "+79001234567"
    }
  ]
}
```

### 3. Удалить станцию из избранного
**DELETE** `/api/user-favorites/{favorite_id}`

**Параметры:**
- `favorite_id` (int) - ID записи в избранном

**Пример запроса:**
```bash
curl -X DELETE http://localhost:8080/api/user-favorites/1
```

**Пример ответа:**
```json
{
  "success": true,
  "message": "Станция удалена из избранного"
}
```

## Коды ошибок

### 400 Bad Request
- `"Отсутствует обязательное поле: user_id"` - не указан user_id
- `"Отсутствует обязательное поле: station_id"` - не указан station_id
- `"Пользователь не найден"` - пользователь с указанным ID не существует
- `"Станция не найдена"` - станция с указанным ID не существует
- `"Станция уже в избранном"` - попытка добавить дубликат
- `"Неверный ID записи"` - неверный формат ID для удаления

### 404 Not Found
- `"Запись в избранном не найдена"` - запись с указанным ID не найдена

## Тестирование

Для тестирования API используйте скрипт `test_user_favorites_api.py`:

```bash
cd optimized_server2
python test_user_favorites_api.py
```

Скрипт выполнит следующие тесты:
1. Получение текущих избранных станций
2. Добавление станции в избранное
3. Проверка добавления
4. Тест дубликата
5. Тест невалидных данных
6. Удаление станции из избранного
7. Проверка удаления

## Структура базы данных

Таблица `user_favorites`:
- `id` (bigint) - первичный ключ
- `user_id` (bigint) - ID пользователя (FK к app_user)
- `station_id` (bigint) - ID станции (FK к station)
- `created_at` (timestamp) - время создания записи

## Ограничения

1. Один пользователь не может добавить одну станцию дважды
2. При удалении пользователя все его избранные станции удаляются автоматически (CASCADE)
3. При удалении станции все связанные записи в избранном удаляются автоматически (CASCADE)

## Интеграция с фронтендом

### JavaScript примеры

**Добавление в избранное:**
```javascript
async function addToFavorites(userId, stationId) {
  const response = await fetch('/api/user-favorites', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      station_id: stationId
    })
  });
  
  const result = await response.json();
  return result;
}
```

**Получение избранных станций:**
```javascript
async function getFavorites(userId) {
  const response = await fetch(`/api/user-favorites?user_id=${userId}`);
  const result = await response.json();
  return result;
}
```

**Удаление из избранного:**
```javascript
async function removeFromFavorites(favoriteId) {
  const response = await fetch(`/api/user-favorites/${favoriteId}`, {
    method: 'DELETE'
  });
  
  const result = await response.json();
  return result;
}
```
