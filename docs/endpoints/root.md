# `GET /`

## Назначение

Возвращает базовую информацию об API: сообщение, версию, ссылку на Swagger UI и основной расчётный эндпойнт.

## Путь выполнения

1. Запрос попадает в `main.py::root`.
2. Код берёт `APP_VERSION` из `constants.py`.
3. Формируется словарь `data` с полями `message`, `version`, `docs`, `unified_endpoint`.
4. Ответ заворачивается через `ResponseWrapper.success_response`.

## Ответ

```json
{
  "success": true,
  "message": "API information retrieved successfully",
  "data": {
    "message": "Manufacturing Calculation API v<APP_VERSION>",
    "version": "<APP_VERSION>",
    "docs": "/docs",
    "unified_endpoint": "/calculate-price"
  },
  "timestamp": "...",
  "version": "<APP_VERSION>"
}
```

## Файлы

- `main.py`
- `constants.py`
- `utils/response_utils.py`
