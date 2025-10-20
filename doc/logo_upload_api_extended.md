# API загрузки логотипов

## Описание

API поддерживает загрузку логотипов организационных единиц двумя способами:
1. **Загрузка файла** - через multipart/form-data
2. **Загрузка по URL** - через JSON с URL изображения

## Эндпоинты

### 1. Загрузка логотипа (файл или URL)

**POST** `/api/org-units/{org_unit_id}/logo`

#### Загрузка файла (multipart/form-data):
```http
POST /api/org-units/123/logo
Content-Type: multipart/form-data
Authorization: Bearer <token>

--boundary
Content-Disposition: form-data; name="logo"; filename="logo.png"
Content-Type: image/png

<binary data>
--boundary--
```

#### Загрузка по URL (JSON):
```http
POST /api/org-units/123/logo
Content-Type: application/json
Authorization: Bearer <token>

{
  "logo_url": "https://example.com/logo.png"
}
```

#### Ответ:
```json
{
  "success": true,
  "data": {
    "logo_url": "/api/logos/123_abc123def456.png",
    "filename": "123_abc123def456.png",
    "source_url": "https://example.com/logo.png"
  },
  "message": "Логотип успешно загружен"
}
```

### 2. Загрузка логотипа по URL

**POST** `/api/org-units/{org_unit_id}/logo-url`

#### Запрос:
```json
{
  "logo_url": "https://example.com/logo.png"
}
```

#### Ответ:
```json
{
  "success": true,
  "data": {
    "logo_url": "/api/logos/123_abc123def456.png",
    "filename": "123_abc123def456.png",
    "source_url": "https://example.com/logo.png"
  },
  "message": "Логотип успешно загружен по URL"
}
```

### 3. Удаление логотипа

**DELETE** `/api/org-units/{org_unit_id}/logo`

#### Ответ:
```json
{
  "success": true,
  "message": "Логотип успешно удален"
}
```

## Ограничения

- **Форматы**: JPG, PNG, GIF, WEBP
- **Размер**: до 15MB
- **URL**: только HTTP/HTTPS, до 2048 символов
- **Таймаут**: 30 секунд для загрузки по URL

## Ошибки

### 400 Bad Request
```json
{
  "success": false,
  "error": "URL логотипа не указан"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Токен авторизации недействителен"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Нет прав доступа к данной организационной единице"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Организационная единица не найдена"
}
```
