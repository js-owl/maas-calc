# Safeguards

## Основной файл

`utils/safeguards.py`, класс `SafeguardManager`.

## Назначение

Safeguards выполняют узкую совместимость входных параметров после объединения request-параметров и извлечённых из файла признаков.

## Что safeguards подставляют

Только два атрибута:

1. `location`.
2. `material_form`.

Другие price-critical параметры не подставляются.

## Путь выполнения

1. `main.py::calculate_price` извлекает параметры из файла через `ParameterExtractor`.
2. `ParameterExtractor.merge_parameters` объединяет извлечённые параметры и request.
3. `main.py` вызывает `safeguard_manager.apply_safeguards(service_id, merged_params)`.
4. Метод копирует параметры в `safeguarded`.
5. Если `location` отсутствует:
   - для `printing` используется `PRINTING_LOCATION`;
   - для остальных сервисов используется `DEFAULTS["location"]`.
6. Если `material_form` отсутствует, но есть `material_id`, `_default_material_form` выбирает первую подходящую форму материала.
7. Если `material_form` есть, `_validate_material_form` проверяет, что форма существует, применима к сервису и имеет положительную цену.
8. Для `cnc-milling` при неподходящем `material_form` допускается fallback на первый доступный полуфабрикат с положительной ценой. Это защищает от устаревшего фронтового дефолта `sheet` для материалов, у которых доступен только `rod`.
9. Возвращается обновлённый словарь параметров.

## Что safeguards не делают

Safeguards не подставляют:

- размеры;
- объём;
- площадь;
- количество;
- material id;
- tolerance;
- finish;
- cover;
- k_otk;
- признаки ML;
- electroplating process;
- толщину покрытия;
- глубину обработки.

Если эти параметры нужны сервису, они должны прийти из запроса, файла или конфигурации конкретного процесса.

## Важное ограничение

`material_form` может быть подобрана автоматически только в рамках `MATERIALS[material_id]["forms"]`. Для `cnc-milling` выбирается форма, применимая к сервису и имеющая положительную цену. Это совместимость для UI/API, а не бизнес-решение о замене материала.
