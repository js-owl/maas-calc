# Стандарт ответа

## Основной файл

`utils/response_utils.py`.

## Success response

`ResponseWrapper.success_response` возвращает:

```json
{
  "success": true,
  "message": "...",
  "data": {},
  "timestamp": "...",
  "version": "..."
}
```

Опционально добавляются:

- `request_id`;
- `metadata`.

## Error response

`ResponseWrapper.error_response` используется для:

- validation errors;
- file processing errors;
- calculation errors;
- service unavailable errors;
- not found errors.

Ответ содержит:

- `error`;
- `error_code`;
- `details`;
- `request_id`;
- `path`;
- `method`;
- `status_code`.

## Важно

В текущем коде часть ошибок возвращается как JSON-объект со статусом внутри body, а не обязательно как HTTP status code. Клиенту нужно смотреть не только HTTP status, но и поля `success`, `error_code`, `status_code`.
