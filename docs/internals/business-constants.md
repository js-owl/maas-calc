# Бизнес-константы

## Основной файл

`constants.py`.

## Централизованные публичные pricing-константы

- `MATERIAL_MARKUP_RATE = 0.20` — наценка на материал.
- `PRINTING_LOCATION = "location_3"` — локация 3D-печати.
- `PRINTING_VOLUME_RESERVE_MM = 30.0` — припуск по габаритам для печати.
- `PRINTING_VOLUME_SPEED_L_PER_HOUR = 6.0` — скорость печати в литрах в час.
- `PRINTING_PREPARATION_TIME_HOURS = 2.0` — ПЗВ для печати.
- `VAT_RATE = 0.22` — НДС/налоговая часть для фронтового breakdown.
- `QUANTITY_DISCOUNT_CONTROL_POINTS` — контрольные точки скидки от количества.
- `ELECTROPLATING_WEIGHT_WORKER_RULES` — нормы количества работников по массе детали.
- `ELECTROPLATING_LABOR_TIME_COEF = 1.18` — коэффициент трудоёмкости гальваники.
- `ELECTROPLATING_BATH_CLEARANCE_MM` — зазор при укладке деталей в ванну.
- `PRACTICAL_GEOMETRIC_CAPACITY_FACTOR` - технологическое снижение загрузки ванны.
- `DEFAULT_ELECTROPLATING_PROCESS_ID` — дефолтный процесс гальваники.
- `COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL` — материал оснастки ПКМ.
- `COMPOSITE_SPECIAL_EQUIPMENT_FORM` — форма материала оснастки ПКМ.
- `COMPOSITE_SPECIAL_EQUIPMENT_MARGIN` — запас габаритов оснастки ПКМ.


## Где используются

- `calculations/core.py` — материал, скидка, стоимость, цикл, проверка машин.
- `calculations/printing.py` — печать.
- `calculations/electroplating.py` — гальваника.
- `calculators/ml_calculator.py` — CNC/composite ML и оснастка.
- `calculators/printing_calculator.py` — breakdown с НДС.
- `calculators/electroplating_calculator.py` — breakdown с НДС.

## Конфиг операционного времени гальваники

В `utils/electroplating_config.py` задан:

```python
ELECTROPLATING_TIME_MODEL_CONFIG = {
    "use_fixed_operation_time_by_process": False,
    "use_thickness_dependent_operation_time": False,
}
```

Он управляет только операционной частью `coating_time_min`.

- `use_fixed_operation_time_by_process=False` означает, что значения из `ELECTROPLATING_FIXED_OPERATION_TIME_MIN_BY_PROCESS` сохраняются в конфиге, но в runtime считаются как `0` минут.
- `use_thickness_dependent_operation_time=False` означает, что Faraday-расчёты по толщине покрытия/оксидного слоя сохраняются в коде, но не добавляют минуты к трудоёмкости.

Подготовительное время, монтаж/демонтаж, количество работников, загрузка ванны и `quantity` продолжают влиять на трудоёмкость независимо от этих флагов.
