# `service_id="composite"`

## Назначение

Автоматический ML-based расчёт изготовления деталей из ПКМ.

## Минимальные входные данные

- `service_id="composite"`;
- `file_data`, `file_name`, `file_type` или `features_dict` с достаточными признаками;
- для файла предпочтительно `stp`/`step`; `stl` отклоняется общей валидацией для composite;
- `material_id`;
- `material_form` или возможность подобрать форму через safeguards;
- `quantity`;
- `is_need_special_equipment`: `0` или `1`, если нужно учитывать оснастку.

## Путь от запроса до ответа

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` проверяет, что `composite` входит в `AUTO_SERVICES`.
3. Выполняется `validate_calculation_request`: service id, материал, форма, количество, файл, file type.
4. Если передан файл, `ParameterExtractor` выбирает `STPExtractor` и извлекает геометрию и признаки.
5. Если `volume` и `surface_area` извлечены, признаки кладутся в `merged_params["ml_features"]`.
6. `SafeguardManager` подставляет только `material_form` и `location`, если они отсутствуют.
7. `CalculationRouter.should_use_ml` для `composite` проверяет доступность `flexible_ensemble` и наличие `volume`, `surface_area`.
8. Если модель недоступна или признаков недостаточно, ML-расчёт не запускается; старой rule-based composite-ветки нет.
9. `CalculationRouter._create_request` создаёт runtime-объект `MLCompositeRequest` и добавляет `is_need_special_equipment`.
10. `MLCompositeCalculator.calculate`:
    - получает material features через `get_material_info`;
    - прогнозирует трудоёмкость через `composite_ml_predictor.predict_from_file_features`;
    - считает трудовую стоимость по `COST_STRUCTURE[location]["price_of_hour"]`;
    - применяет `k_quantity`, `k_cover`, `k_otk`;
    - считает стоимость композиционного материала через `_calculate_composite_material_costs`;
    - если `is_need_special_equipment == 1`, считает материал оснастки через `_calculate_composite_special_equipment_material_costs`;
    - трудоёмкость оснастки считается эвристикой `predicted_hours * SPECIAL_EQUIPMENT_COEF`;
    - стоимость оснастки распределяется на `quantity`;
    - итоговая цена считается через `calculate_cost`.
11. Возвращается `UnifiedCalculationResponse` с ML-прогнозом, breakdown, material costs и tooling breakdown.
12. `main.py` добавляет `filename`, выставляет `calculation_engine="ml_model"` и возвращает success response.

## Оснастка ПКМ

По умолчанию используется:

- `COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL = "mdf"`;
- `COMPOSITE_SPECIAL_EQUIPMENT_FORM = "plate"`;
- `COMPOSITE_SPECIAL_EQUIPMENT_MARGIN = 1.2`.

Материал оснастки берётся из `DOP_MATERIALS`. Если оснастка нужна, но данные MDF-плиты не настроены, расчёт должен завершиться ошибкой.

## Основные файлы

- `main.py`
- `utils/parameter_extractor.py`
- `extractors/stp_extractor.py`
- `utils/calculation_router.py`
- `calculators/ml_calculator.py`
- `utils/composite_ml_predictor.py`
- `calculations/core.py`
- `constants.py`
