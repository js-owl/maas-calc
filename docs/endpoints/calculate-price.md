# `POST /calculate-price`

## Назначение

Основной эндпойнт расчёта стоимости. Принимает `UnifiedCalculationRequest` и возвращает стандартный ответ с `UnifiedCalculationResponse` внутри `data`.

## Поддерживаемые группы `service_id`

1. Автоматический расчёт из `constants.AUTO_SERVICES`:
   - `printing`
   - `cnc-milling`
   - `composite`
   - `electroplating_auto`

2. Ручная оценка из `constants.OTHER_SERVICES`:
   - `bending`
   - `handing`
   - `heating`
   - `laser-cutting`
   - `grinding`
   - `welding`
   - `casting`
   - `other`
   - `testing`
   - `rubber`

Для ручных сервисов эндпойнт сразу возвращает успешный ответ с ценой `0` и `calculation_method="manual_pricing"`. Извлечение файла, валидации автоматического расчёта, safeguards и роутер для них не запускаются.

## Общий путь автоматического расчёта

1. Запрос попадает в `main.py::calculate_price`.
2. Выполняется логирование старта через `log_calculation_start`.
3. Код собирает списки `AUTO_SERVICES_LIST` и `OTHER_SERVICES_LIST` из `constants.py`.
4. Если `service_id` находится в `OTHER_SERVICES_LIST`, возвращается successful zero-price response.
5. Если `service_id` не находится ни в `AUTO_SERVICES_LIST`, ни в `OTHER_SERVICES_LIST`, возвращается calculation error.
6. Для `cnc-milling` проверяется наличие `file_data`. Текущий runtime для CNC — только ML.
7. Для `electroplating_auto` требуется либо `file_data`, либо `features_dict`.
8. Выполняется `validate_calculation_request` из `utils/validation_utils.py`.
9. Если переданы `file_data`, `file_name`, `file_type`, вызывается `ParameterExtractor.extract_parameters_from_file`.
10. Извлечённые параметры объединяются с параметрами запроса через `ParameterExtractor.merge_parameters`; значения из запроса имеют приоритет.
11. Если извлечены `volume` и `surface_area`, все извлечённые признаки кладутся в `merged_params["ml_features"]`. Для `electroplating_auto` также допускается прямой `features_dict`.
12. Запускается `SafeguardManager.apply_safeguards`, который подставляет только `material_form` и `location`.
13. `CalculationRouter.should_use_ml` определяет, нужен ли ML.
14. `CalculationRouter.route_calculation` создаёт внутренний request и вызывает нужный калькулятор.
15. К результату добавляются `filename` и `calculation_engine`.
16. Ответ заворачивается в `ResponseWrapper.success_response`.

## Файлы

- `main.py`
- `models/request_models.py`
- `models/response_models.py`
- `utils/validation_utils.py`
- `utils/parameter_extractor.py`
- `utils/safeguards.py`
- `utils/calculation_router.py`
- `calculators/printing_calculator.py`
- `calculators/electroplating_calculator.py`
- `calculators/ml_calculator.py`

## Детальные service-specific маршруты

- [`printing`](../service_ids/printing.md)
- [`cnc-milling`](../service_ids/cnc-milling.md)
- [`composite`](../service_ids/composite.md)
- [`electroplating_auto`](../service_ids/electroplating_auto.md)
- [ручные сервисы](../service_ids/bending.md)
