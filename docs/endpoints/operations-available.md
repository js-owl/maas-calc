# `GET /operations_available`

## Назначение

Возвращает операции, доступные для выбранного `service_id`.

## Query-параметры

- `service_id`: обязательный service id.

## Путь выполнения

1. Запрос попадает в `main.py::list_operations_available`.
2. Если `service_id` равен `electroplating_auto` или неавтоматическому `electroplating`, возвращаются операции из `utils.electroplating_config.get_process_params()`.
3. Для каждой гальванической операции формируется:
   - `id`;
   - `group`;
   - `path`;
   - `label`;
   - `max_part_size_mm`;
   - `max_part_size_label`;
   - `max_weight_kg`;
   - `material_families`;
   - `profile_key`;
   - признаки необходимости ввода толщины/глубины обработки.
4. Если `service_id` найден в `NON_AUTO_SERVICES`, возвращаются его `operations`, если они заданы.
5. Если операций нет, возвращается `{"values": []}`.

## Файлы

- `main.py`
- `constants.py`
- `utils/electroplating_config.py`
