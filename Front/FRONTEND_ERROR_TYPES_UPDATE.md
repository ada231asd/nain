# Обновление фронтенда для работы с новыми типами ошибок

## Выполненные изменения

### 1. API Client (pythonApi.js)
- ✅ Добавлен метод `getPowerbankErrorTypes()` для получения типов ошибок с сервера
- ✅ Добавлен метод `returnError()` для возврата с ошибкой (новый API)
- ✅ Увеличен timeout до 35 секунд для Long Polling

### 2. ErrorReportModal.vue
- ✅ Убраны старые статичные типы ошибок
- ✅ Добавлена загрузка типов ошибок с сервера через `getPowerbankErrorTypes()`
- ✅ Добавлен fallback на старые типы в случае ошибки загрузки
- ✅ Добавлен импорт `onMounted` для инициализации

### 3. Dashboard.vue
- ✅ Обновлен вызов API с `returnDamaged()` на `returnError()`
- ✅ Изменен параметр с `error_type` на `error_type_id`
- ✅ Обновлено время ожидания с 11 до 30 секунд

## Новый формат API

### Получение типов ошибок
```javascript
const response = await pythonAPI.getPowerbankErrorTypes()
// Возвращает: { success: true, error_types: [{ id_er: 1, type_error: "..." }] }
```

### Возврат с ошибкой
```javascript
const response = await pythonAPI.returnError({
  station_id: 13,
  user_id: 32,
  error_type_id: 1  // ID из БД (1-4)
})
```

## Типы ошибок из БД

| ID | Описание |
|----|----------|
| 1  | Аккумулятор не заряжает |
| 2  | Сломан Type C |
| 3  | Сломан Micro usb |
| 4  | Сломан liting |

## Результат

- ✅ Фронтенд теперь использует типы ошибок из базы данных
- ✅ API совместим с обновленным сервером
- ✅ Long Polling работает корректно (30 секунд)
- ✅ Есть fallback на старые типы в случае ошибки
