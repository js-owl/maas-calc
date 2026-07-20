# `GET /auto_services`

## Назначение

Возвращает сервисы, для которых есть автоматический расчёт цены.

## Путь выполнения

1. Запрос попадает в `main.py::list_auto_services`.
2. Код преобразует `constants.AUTO_SERVICES` в список объектов `{id, label, service}`.
3. Ответ возвращается через `ResponseWrapper.success_response`.

## Текущий список

- `printing`
- `cnc-milling`
- `composite`
- `electroplating_auto`

## Файлы

- `main.py`
- `constants.py`
