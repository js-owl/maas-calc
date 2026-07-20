# `GET /materials`

## Назначение

Возвращает список материалов из `constants.MATERIALS`, при необходимости фильтрует их по процессу.

## Query-параметры

- `process`: необязательный service/process id.
- `electroplating_process_id`: необязательный ID операции для `process=electroplating_auto`.

## Путь выполнения

1. Запрос попадает в `main.py::list_materials`.
2. Если `process=electroplating_auto` и передан `electroplating_process_id`, process id проверяется через `get_electroplating_process`.
3. Код проходит по `MATERIALS_gen.MATERIALS`.
4. Для `electroplating_auto` материал пропускается, если его `electroplating_family` не подходит выбранной операции.
5. Для остальных process id материал пропускается, если process отсутствует в `material_info["applicable_processes"]`.
6. Для каждого подходящего материала строится payload через `_material_response_item`.
7. Список сортируется по `label`.
8. Ответ возвращается через `ResponseWrapper.success_response`.

## Ответ

`data.materials[]` содержит:

- `id`;
- `label`;
- `family`;
- `density`;
- `forms`;
- `available_forms`;
- `applicable_processes`;
- `electroplating_family`.

## Файлы

- `main.py`
- `constants.py`
- `utils/electroplating_config.py`
