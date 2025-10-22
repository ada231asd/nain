# Документация API для фронтенд разработчика

## Аутентификация

Все запросы (кроме логина) требуют JWT токен в заголовке:
Authorization: Bearer {your_jwt_token}


## Основные эндпоинты

1. Логин
POST /api/auth/login
Тело: {"phone_e164": "+79001234567", "password": "password123"}

2. Получить доступные повербанки
GET /api/user/powerbanks/available

3. Получить список станций
GET /api/user/stations

4. Взять повербанк
POST /api/user/powerbanks/borrow
Тело: {"station_id": 13}


5. Получить заказы пользователя
GET /api/user/orders

6. Получить профиль пользователя
GET /api/user/profile


## Форматы ответов

Логин:
{
    "success": true,
  "token": "jwt_token_here",
  "user": {"user_id": 33, "fio": "Иван Иванов", "role": "user"}
}

GET /api/user/powerbanks/available
Доступные повербанки:
{
  "success": true,
  "data": {
    "available_powerbanks": [
      {
        "powerbank_id": 54,
        "serial_number": "DCHA54000015",
        "soh": 100,
        "status": "active"
      }
    ],
    "count": 1,
    "user_limits": {
      "max_limit": 2,
      "current_borrowed": 1,
      "available_by_limit": 1
    }
  }
}

 Получить список станций
Станции:
{
  "success": true,
  "data": {
    "stations": [
      {
        "std": ation_13,
        "box_id": "DCHEY02504000019",
        "slots_declared": 8,
        "remain_num": 3,
        "status": "active"
      }
    ]
  }
}
POST /api/user/powerbanks/borrow
Взять повербанк:
{
  "success": true,
  "data": {
    "message": "Повербанк успешно выдан",
    "order_id": 101,
    "powerbank_serial": "DCHA54000015",
    "station_box_id": "DCHEY02504000019",
    "user_limits": {
      "max_limit": 2,
      "current_borrowed": 1,
      "available_by_limit": 1
    }
  }
}


## Типовой сценарий использования

1. Получить доступные повербанки - показываем сколько можно взять
2. Получить список станций - показываем доступные станции
3. Взять повербанк - отправляем только station_id
4. Обновить интерфейс - уменьшаем счетчик доступных

Пример кода:

// Получаем доступные повербанки
const availableResponse = await fetch('/api/user/powerbanks/available', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const availableData = await availableResponse.json();

// Показываем: "Вы можете взять X повербанков"
const canTakeCount = availableData.data.user_limits.available_by_limit;

// Берем повербанк
const borrowResponse = await fetch('/api/user/powerbanks/borrow', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({station_id: selectedStationId})
});


## Особенности

- Сервер сам выбирает повербанк (фронтенд не выбирает конкретный)
- Количество доступных повербанков ограничено лимитом пользователя
- После каждой операции возвращаются актуальные лимиты
- Проверяется онлайн-статус станций


## Ошибки

Общие:
- 401 Unauthorized - невалидный токен
- 403 Forbidden - нет доступа
- 503 Service Unavailable - станция офлайн

Сообщения:
{"success": false, "message": "Лимит повербанков исчерпан"}
{"success": false, "message": "Станция не подключена"}