# `GET /services`

## Назначение

Возвращает плоский список service id из трёх справочников:

- `AUTO_SERVICES`;
- `OTHER_SERVICES`;
- `NON_AUTO_SERVICES`.

## Путь выполнения

1. Запрос попадает в `main.py::list_services`.
2. Код берёт поле `service` из каждого элемента `AUTO_SERVICES`, `OTHER_SERVICES`, `NON_AUTO_SERVICES`.
3. Возвращает список через `ResponseWrapper.success_response`.

## Важно

Наличие service id в `/services` не означает, что `/calculate-price` выполнит автоматический расчёт. Автоматический расчёт выполняется только для `AUTO_SERVICES`; успешный нулевой ответ выполняется только для `OTHER_SERVICES`.

## Файлы

- `main.py`
- `constants.py`
