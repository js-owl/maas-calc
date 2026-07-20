# `GET /all_services`

## Назначение

Возвращает общий список сервисов для UI-справочника.

## Путь выполнения

1. Запрос попадает в `main.py::list_all_services`.
2. В список добавляются элементы из `AUTO_SERVICES`.
3. Затем добавляются элементы из `OTHER_SERVICES`.
4. Затем добавляются элементы из `NON_AUTO_SERVICES`.
5. Ответ возвращается через `ResponseWrapper.success_response`.

## Важно

Этот endpoint справочный. Он не является источником истины о том, какие service id поддерживают автоматический расчёт. Для этого использовать `/auto_services` и документацию по `/calculate-price`.

## Файлы

- `main.py`
- `constants.py`
