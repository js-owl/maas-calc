# `service_id="cnc-milling"`

## Назначение

Автоматический ML-only расчёт механической обработки. Текущий runtime для CNC — только ML.

## Минимальные входные данные

- `service_id="cnc-milling"`;
- `file_data`, `file_name`, `file_type`;
- `file_type` должен быть `stp` или `step`; `stl` для CNC отклоняется;
- `material_id`;
- `material_form` или возможность подобрать форму через safeguards;
- `quantity`;
- `location` или дефолтная локация из `DEFAULTS`.

## Путь от запроса до ответа

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` проверяет, что `cnc-milling` входит в `AUTO_SERVICES`.
3. `main.py` отдельно проверяет наличие `file_data`. Без файла возвращается calculation error.
4. Выполняется `validate_calculation_request`:
   - проверяется `service_id`;
   - проверяется материал и форма;
   - проверяются `quantity`, `tolerance_id`, `finish_id`, `cover_id`, если они переданы;
   - проверяется, что `file_type` не `stl`.
5. `ParameterExtractor` выбирает `STPExtractor` для `stp`/`step`.
6. `STPExtractor` через CADQuery/OCP извлекает `volume`, `surface_area`, OBB-размеры, топологические и геометрические признаки.
7. Извлечённые признаки кладутся в `merged_params["ml_features"]`.
8. `SafeguardManager` подставляет только `material_form` и `location`, если они отсутствуют.
9. `CalculationRouter.should_use_ml` проверяет:
   - `ENABLE_ML_MODELS`;
   - доступность `flexible_ensemble` через `composite_ml_predictor.is_model_available()`;
   - доступность XGBoost-классификатора через `ml_predictor.is_classifier_available()`;
   - наличие `volume` и `surface_area` в `ml_features`.
10. Если хотя бы одно условие не выполнено, расчёт падает с ошибкой. Старой rule-based ветки нет.
11. `CalculationRouter._create_request` создаёт runtime-объект `MLCNCMillingRequest`.
12. `MLCNCMillingCalculator.calculate` наследует логику `MLCalculator.calculate`.
13. `MLCalculator.calculate`:
    - проверяет подходящие станки через `check_machines`;
    - собирает material features через `get_material_info`;
    - если фронт прислал устаревший `material_form` (например, `sheet`), а у выбранного материала есть только другой priced-полуфабрикат (`rod`), `get_material_info` через `resolve_priced_material_form` подставляет доступную форму с положительной ценой;
    - прогнозирует трудоёмкость через `composite_ml_predictor.predict_from_file_features`;
    - прогнозирует `is_need_special_equipment` через `ml_predictor.predict_special_equipment_from_file_features`;
    - считает трудовую стоимость по `COST_STRUCTURE[location]["price_of_hour"]`;
    - применяет `k_quantity`, `k_cover`, `k_otk`, `k_tolerance`, `k_finish`;
    - считает стоимость материала по OBB-заготовке;
    - считает стоимость технологической оснастки при положительном флаге классификатора;
    - распределяет стоимость оснастки на `quantity`;
    - считает итог через `calculate_cost`.
14. Возвращается `UnifiedCalculationResponse` с ML-прогнозом, breakdown, features summary и material costs.
15. `main.py` добавляет `filename`, выставляет `calculation_engine="ml_model"` и возвращает success response.

## Fallback по полуфабрикату материала

Для CNC есть отдельная защита от нулевой цены материала. Исторически фронт мог отправлять `material_form="sheet"` как дефолт. У части материалов для CNC (`non_ferrous_БрАЖМц10-3-1.5`, `non_ferrous_Л63`, `steel_40Х13`, `steel_Ст45`) доступен только `rod`. Раньше это приводило к `price_per_kg=0` и нулевой material cost.

Теперь путь такой:

1. Валидация `material_form` для `service_id="cnc-milling"` не отклоняет запрос, если для материала можно найти другой применимый полуфабрикат с положительной ценой.
2. `SafeguardManager` заменяет неподходящий/неоценённый `material_form` на результат `resolve_priced_material_form`.
3. `MLCalculator` вызывает `get_material_info(material_id, material_form, service_id)`.
4. В `material_costs` и `total_price_breakdown` попадают диагностические поля:
   - `requested_material_form`;
   - `material_form` — фактически использованная форма;
   - `material_form_fallback_applied`.

Если положительную цену найти нельзя, CNC material cost больше не должен молча превращаться в `0`; расчёт должен падать controlled error.

## Основные файлы

- `main.py`
- `utils/parameter_extractor.py`
- `extractors/stp_extractor.py`
- `utils/calculation_router.py`
- `calculators/ml_calculator.py`
- `utils/composite_ml_predictor.py`
- `utils/ml_predictor.py`
- `calculations/core.py`
- `constants.py`
