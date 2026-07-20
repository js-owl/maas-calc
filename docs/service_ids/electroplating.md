# `service_id="electroplating"`

## Назначение

Неавтоматический справочный service id из `constants.NON_AUTO_SERVICES`. Используется для UI-операций и списка доступных операций, но не является успешным service id для `/calculate-price`.

## Путь в `/operations_available`

1. Запрос `GET /operations_available?service_id=electroplating` попадает в `main.py::list_operations_available`.
2. Код видит, что `service_id` равен `NON_AUTO_ELECTROPLATING_SERVICE`.
3. Возвращаются операции из `utils.electroplating_config.get_process_params()`.

## Путь в `/calculate-price`

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` проверяет `OTHER_SERVICES_LIST` и `AUTO_SERVICES_LIST`.
3. `electroplating` не входит в `OTHER_SERVICES` и не входит в `AUTO_SERVICES`.
4. Возвращается calculation error.

## Для автоматического расчёта

Использовать [`service_id="electroplating_auto"`](electroplating_auto.md).

## Основные файлы

- `main.py`
- `constants.py::NON_AUTO_SERVICES`
- `utils/electroplating_config.py`
