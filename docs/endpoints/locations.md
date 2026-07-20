# `GET /locations`

## Назначение

Возвращает производственные локации из `constants.LOCATIONS`.

## Путь выполнения

1. Запрос попадает в `main.py::list_locations_endpoint`.
2. Код преобразует `LOCATIONS` в список объектов `{id, ...}`.
3. Ответ возвращается через `ResponseWrapper.success_response`.

## Файлы

- `main.py`
- `constants.py`
