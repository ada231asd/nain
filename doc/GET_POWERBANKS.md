## GET /api/powerbanks (старая API)

GET /api/powerbanks

Query params (optional):
- page: number (default 1)
- limit: number (default 100)
- status: one of [active, system_error, written_off, unknown]
- org_unit_id: number

Response:
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "org_unit_id": 10,
      "serial_number": "PB-12345",
      "soh": 87,
      "status": "active",
      "write_off_reason": "none",
      "created_at": "2025-10-30T12:34:56+03:00",
      "power_er": null,
      "is_deleted": 0,
      "deleted_at": null,
      "org_unit_name": "Городская больница №1",
      "error_type": null,

      "station_id": 45,
      "station_box_id": "ST-00045",
      "station_slot_number": 7,

      "active_order_id": 9988,
      "active_order_status": "borrow",
      "active_order_timestamp": "2025-10-30T12:40:01+03:00",
      "active_order_user_phone": "+79991112233",
      "active_order_station_box_id": "ST-00045"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 100,
    "total": 250,
    "pages": 3
  }
}
```



