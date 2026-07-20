# `GET /version`

## Назначение

Возвращает информацию о версии API.

## Путь выполнения

1. Запрос попадает в `main.py::get_version`.
2. Вызывается `utils.versioning.get_version_info()`.
3. Ответ заворачивается через `ResponseWrapper.success_response`.

## Файлы

- `main.py`
- `utils/versioning.py`
- `utils/response_utils.py`
