# Валидации

## Основной файл

`utils/validation_utils.py`.

## Когда запускаются

Валидации запускаются в `main.py::calculate_price` только для автоматических сервисов. Для service id из `OTHER_SERVICES` endpoint возвращает manual-pricing response до вызова `validate_calculation_request`.

## Общий порядок

`validate_calculation_request(request_data)` выполняет проверки и возвращает список `ValidationError`. Если список не пустой, `main.py` возвращает validation error через `create_validation_error_response`.

## Проверки

### `service_id`

`Validator.validate_service_id` проверяет, что service id входит в общий список из:

- `AUTO_SERVICES`;
- `OTHER_SERVICES`;
- `NON_AUTO_SERVICES`.

Важно: прохождение этой проверки не означает, что `/calculate-price` выполнит расчёт. До валидации `main.py` отдельно отсеивает service id, которые не входят в `AUTO_SERVICES` и `OTHER_SERVICES`.

### `material_id`

`Validator.validate_material_id` проверяет:

- материал существует в `MATERIALS`;
- для обычных auto-сервисов material id применим к `service_id`;
- для `electroplating_auto` материал должен иметь допустимый `electroplating_family`.

### `material_form`

`Validator.validate_material_form` проверяет:

- форма есть в `MATERIALS[material_id]["forms"]`;
- для обычных auto-сервисов форма применима к `service_id`;
- для `cnc-milling` неподходящая форма не считается ошибкой, если `resolve_priced_material_form` может найти применимый полуфабрикат с положительной ценой;
- для `electroplating_auto` form-level `applicable_processes` не используется как критерий пригодности, потому что гальваника работает через family/process compatibility.

### `quantity`

`quantity` должен быть целым числом `> 0`.

### `tolerance_id`, `finish_id`, `cover_id`

- `tolerance_id` проверяется по `TOLERANCE`.
- `finish_id` проверяется по `FINISH`.
- `cover_id` для обычных сервисов проверяется по `COVER`.
- `cover_id` для `electroplating_auto` трактуется как совместимый способ передать process id через первый элемент списка.

### `file_data`, `file_name`, `file_type`

Если все три поля переданы, проверяется:

- непустой `file_data`;
- непустой `file_name`;
- непустой `file_type`;
- `file_type` входит в `stl`, `stp`, `step`.

### Соответствие `file_type` сервису

`stl` отклоняется для:

- `cnc-milling`;
- `composite`;
- `electroplating_auto`.

### `electroplating_auto`

Дополнительно проверяется:

- process id существует;
- `electroplating_family` существует;
- если переданы и `electroplating_family`, и `material_id`, они описывают одну family;
- process совместим с family;
- `coating_thickness_microns` неотрицательная;
- `processing_depth_microns` неотрицательная.

## Ошибки

Ошибки собираются в `ErrorDetail` и возвращаются через `ResponseWrapper.error_response` с типом `validation`.
