# Маршрутизация расчёта

## Основной объект

Маршрутизация находится в `utils/calculation_router.py`, класс `CalculationRouter`.

## Активные маршруты

- `printing` → `PrintingCalculator`, rule-based.
- `electroplating_auto` → `ElectroplatingAutoCalculator`, rule-based.
- `cnc-milling` → `MLCNCMillingCalculator`, ML-only.
- `composite` → `MLCompositeCalculator`, ML-based.

## Путь выполнения

1. `main.py::calculate_price` передаёт `service_id`, `safeguarded_params` и `use_ml` в `route_calculation`.
2. `route_calculation` вызывает `_get_calculator`.
3. `_get_calculator` лениво создаёт калькулятор и кэширует его по ключу `service_id + режим`.
4. `_create_request` создаёт внутренний request-объект под выбранный калькулятор.
5. Вызывается `calculator.calculate(request)`.

## ML-логика

`should_use_ml` работает так:

- `printing` → всегда `False`;
- `electroplating_auto` → всегда `False`;
- `composite` → `True`, если доступна модель и есть `volume`, `surface_area`;
- `cnc-milling` → `True` только если включены ML-модели, доступна labor-модель, доступен classifier и есть `volume`, `surface_area`.

Для `cnc-milling` отсутствие ML-условий является ошибкой. Альтернативный rule-based расчёт отсутствует.
