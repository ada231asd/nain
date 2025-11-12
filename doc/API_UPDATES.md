# API Updates (auto-approval `aprof`)

## POST `/api/org-units`

### Request
```json
{
  "unit_type": "group",
  "name": "Updated Test Organization",
  "adress": "Москва, ул. Пушкина",
  "logo_url": "https://cdn.example/logo.png",
  "default_powerbank_limit": 5,
  "reminder_hours": 12,
  "write_off_hours": 24,
  "aprof": 1
}
```

### Response
```json
{
  "success": true,
  "data": {
    "org_unit_id": 136
  },
  "message": "Организационная единица создана"
}
```

## PUT `/api/org-units/{org_unit_id}`

### Request
```json
{
  "name": "Updated Test Organization",
  "aprof": 0
}
```

### Response
```json
{
  "success": true,
  "message": "Организационная единица обновлена"
}
```

## GET `/api/org-units`

### Response
```json
{
  "success": true,
  "data": [
    {
      "org_unit_id": 136,
      "parent_org_unit_id": null,
      "unit_type": "group",
      "name": "Updated Test Organization",
      "adress": "Москва, ул. Пушкина",
      "logo_url": "https://cdn.example/logo.png",
      "created_at": "2025-11-07T10:12:39",
      "default_powerbank_limit": 5,
      "reminder_hours": 12,
      "write_off_hours": 24,
      "aprof": 1,
      "is_deleted": 0,
      "deleted_at": null,
      "parent_name": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 100,
    "total": 1,
    "pages": 1
  }
}
```

## GET `/api/org-units/{org_unit_id}`

### Response
```json
{
  "success": true,
  "data": {
    "org_unit_id": 136,
    "parent_org_unit_id": null,
    "unit_type": "group",
    "name": "Updated Test Organization",
    "adress": "Москва, ул. Пушкина",
    "logo_url": "https://cdn.example/logo.png",
    "created_at": "2025-11-07T10:12:39",
    "default_powerbank_limit": 5,
    "reminder_hours": 12,
    "write_off_hours": 24,
    "aprof": 1,
    "is_deleted": 0,
    "deleted_at": null,
    "parent_name": null
  }
}
```

## POST `/api/invitations/register`

### Response (auto-approval when `aprof = 1`)
```json
{
  "success": true,
  "message": "Регистрация прошла успешно. Аккаунт активирован.",
  "user_id": 512,
  "status": "active",
  "org_unit_id": 136,
  "role": "user"
}
```

### Response (approval required when `aprof = 0`)
```json
{
  "success": true,
  "message": "Регистрация прошла успешно. Пароль отправлен на email. Ожидает подтверждения администратора.",
  "user_id": 513,
  "status": "pending",
  "org_unit_id": 137,
  "role": "user"
}
```

### Field description

`aprof` — флаг авто-одобрения (0 — требуется утверждение, 1 — активируется автоматически).

