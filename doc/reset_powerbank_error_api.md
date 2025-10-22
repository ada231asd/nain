# API для сброса ошибок аккумуляторов

## POST /api/powerbanks/{powerbank_id}/reset-error

Сбрасывает ошибку у аккумулятора и переводит его в статус `active`.

**URL параметры:**
- `powerbank_id` (int) - ID аккумулятора

**Действия:**
- Обнуляет поле `power_er`
- Устанавливает статус `active`

**Успешный ответ (200):**
```json
{
  "success": true,
  "message": "Ошибка повербанка успешно сброшена",
  "powerbank_id": 42,
  "serial_number": "PB-12345678"
}
```

**Ошибка - не найден (404):**
```json
{
  "success": false,
  "error": "Аккумулятор не найден"
}
```

**Ошибка - неверный ID (400):**
```json
{
  "success": false,
  "error": "Неверный ID аккумулятора"
}
```

**Внутренняя ошибка (500):**
```json
{
  "success": false,
  "error": "Ошибка сброса ошибки powerbank: ..."
}
```
