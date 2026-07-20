# `GET /electroplating_material_families`

## Назначение

Возвращает семейства материалов, доступные для `electroplating_auto`. Может фильтровать семьи под конкретный `electroplating_process_id`.

## Query-параметры

- `electroplating_process_id`: необязательный ID операции гальваники.

## Путь выполнения

1. Запрос попадает в `main.py::list_electroplating_material_families`.
2. Если передан `electroplating_process_id`, он проверяется через `get_electroplating_process`.
3. Если process id неизвестен, возвращается validation error.
4. Вызывается `get_material_families_for_process(electroplating_process_id)`.
5. Семейства сортируются по label.
6. Ответ возвращается через `ResponseWrapper.success_response`.

## Ответ

`data.values[]` содержит:

- `id`;
- `label`;
- `density_kg_dm3`;
- `allowed_processes`.

## Файлы

- `main.py`
- `utils/electroplating_config.py`
