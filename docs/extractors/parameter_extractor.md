# `ParameterExtractor`

## Файл

`utils/parameter_extractor.py`.

## Назначение

Координатор извлечения параметров из CAD-файла. Сам геометрию не считает, а выбирает специализированный extractor по `file_type`.

## Поддерживаемые типы

- `stl` → `STLExtractor`;
- `stp` → `STPExtractor`;
- `step` → `STPExtractor`.

## Путь выполнения

1. `main.py::calculate_price` вызывает `extract_parameters_from_file(file_data, file_name, file_type)`.
2. `ParameterExtractor` выбирает extractor из `self.extractors`.
3. Если extractor отсутствует, возвращается `{}`.
4. Если extractor найден, вызывается `extractor.extract_parameters(...)`.
5. При ошибке логируется exception и возвращается `{}`.
6. После извлечения `merge_parameters(extracted_params, request_params)` объединяет данные.

## Приоритет объединения

`merge_parameters` сначала кладёт извлечённые параметры, затем поверх них кладёт непустые значения из request. То есть request имеет приоритет над extractor output.

## Использование результата

Если после извлечения есть `volume` и `surface_area`, `main.py` кладёт весь набор признаков в `merged_params["ml_features"]`.
