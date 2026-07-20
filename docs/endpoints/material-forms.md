# `GET /material_forms`

## Назначение

Возвращает формы материала для выбранного `material_id`.

## Query-параметры

- `material_id`: обязательный ID материала.
- `service_id`: необязательный service id для проверки применимости формы.
- `electroplating_process_id`: необязательный ID операции для `service_id=electroplating_auto`.

## Путь выполнения

1. Запрос попадает в `main.py::list_material_forms`.
2. `material_id` ищется в `MATERIALS_gen.MATERIALS`.
3. Если материал неизвестен, возвращается validation error.
4. Для `service_id=electroplating_auto` дополнительно проверяется:
   - существует ли `electroplating_process_id`, если он передан;
   - допустим ли материал для выбранной гальванической операции.
5. Для остальных service id проверяется наличие service id в `material_info["applicable_processes"]`.
6. Формы строятся через `_material_form_response_items` из `material_info["forms"]`. Endpoint не синтезирует fallback-форму; fallback применяется только во входном расчёте `cnc-milling`, если клиент прислал устаревшую форму.
7. Ответ возвращается через `ResponseWrapper.success_response`.

## Ответ

`data.material_forms[]` содержит:

- `id`;
- `label`;
- `price`;
- `applicable_processes`;
- `one_layer_thickness`.

## Файлы

- `main.py`
- `constants.py`
- `utils/electroplating_config.py`
