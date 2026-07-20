# `service_id="printing"`

## Назначение

Автоматический rule-based расчёт 3D-печати.

## Минимальные входные данные

- `service_id="printing"`;
- `dimensions` или CAD-файл, из которого можно извлечь размеры;
- `material_id`;
- `material_form` или возможность подобрать форму из `MATERIALS[material_id]["forms"]`;
- `quantity`.

`location` в расчёте принудительно используется как `PRINTING_LOCATION` из `constants.py`. Сейчас это `location_3`, потому что принтеры есть только в этой локации.

## Путь от запроса до ответа

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` проверяет, что `printing` входит в `AUTO_SERVICES`.
3. Выполняется `validate_calculation_request`:
   - проверяется `service_id`;
   - если передан `material_id`, проверяется его наличие и применимость к `printing`;
   - если передан `material_form`, проверяется форма;
   - проверяется `quantity`, если он передан;
   - проверяются `cover_id`, `file_data`, `file_type`, если они переданы.
4. Если передан файл, `ParameterExtractor` выбирает `STLExtractor` или `STPExtractor` и получает геометрию.
5. `ParameterExtractor.merge_parameters` объединяет извлечённые параметры и request-параметры; request имеет приоритет.
6. `SafeguardManager` подставляет только `material_form`, если она отсутствует, и `location`; для `printing` location становится `PRINTING_LOCATION`.
7. `CalculationRouter.should_use_ml` возвращает `False`.
8. `CalculationRouter._create_request` создаёт `PrintingCalculationRequest`.
9. `PrintingCalculator.calculate` вызывает `calculations.printing.calculate_printing_price`.
10. `calculate_printing_price`:
    - проверяет подходящие машины через `check_machines`;
    - получает свойства материала через `resolve_material`;
    - рассчитывает объём заготовки с reserve `PRINTING_VOLUME_RESERVE_MM`;
    - считает массу и billable weight с учётом MOQ;
    - считает цену материала через `calculate_mat_price`;
    - считает время печати через `calculate_printing_work_time`;
    - считает трудовую стоимость по `COST_STRUCTURE[PRINTING_LOCATION]["price_of_hour"]`;
    - применяет `k_quantity`, `k_cover`, `k_otk`;
    - считает цену через `calculate_cost`;
    - считает производственный цикл через `calculate_cycle`.
11. `PrintingCalculator` формирует breakdown для фронта и возвращает `UnifiedCalculationResponse`.
12. `main.py` добавляет `filename`, выставляет `calculation_engine="rule_based"` и возвращает success response.

## Основные файлы

- `main.py`
- `models/calculation_models.py::PrintingCalculationRequest`
- `utils/calculation_router.py`
- `calculators/printing_calculator.py`
- `calculations/printing.py`
- `calculations/core.py`
- `constants.py`
