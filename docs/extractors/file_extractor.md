# `FileParameterExtractor`

## Файл

`extractors/file_extractor.py`.

## Назначение

Базовый класс для CAD-экстракторов. Содержит общую работу с временными файлами.

## Методы

### `extract_parameters`

Абстрактный метод. Должен быть реализован в наследниках.

### `_save_temp_file`

1. Декодирует `file_data` из base64.
2. Создаёт временный файл через `tempfile.NamedTemporaryFile(delete=False)`.
3. Использует suffix из исходного `file_name`.
4. Записывает bytes во временный файл.
5. Возвращает `Path` к файлу.

### `_cleanup_temp_file`

Удаляет временный файл после анализа.

### `_extract_dimensions_from_bounds`

Вспомогательный метод для получения `Dimensions` из bounding box вида `{min, max}`. В текущих специализированных экстракторах основной путь идёт через OBB/геометрию конкретного формата.
