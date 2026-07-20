# `service_id="electroplating_auto"`

## Назначение

Автоматический rule-based расчёт нанесения гальванических и химических покрытий по геометрии STP/STEP-модели.

## Рекомендуемый flow для фронта

1. `GET /operations_available?service_id=electroplating_auto` — получить список операций.
2. `GET /electroplating_material_families?electroplating_process_id=<process_id>` — получить допустимые семейства материалов.
3. `GET /materials?process=electroplating_auto&electroplating_process_id=<process_id>` — получить конкретные материалы, если UI работает через `material_id`.
4. `GET /material_forms?service_id=electroplating_auto&electroplating_process_id=<process_id>&material_id=<material_id>` — получить формы выбранного материала.
5. `POST /calculate-price` — отправить расчётный запрос.

## Минимальные входные данные

- `service_id="electroplating_auto"`;
- `file_data`, `file_name`, `file_type="stp"/"step"` или `features_dict`;
- `electroplating_process_id` или первый элемент `cover_id` как совместимый способ передачи process id;
- `electroplating_family` или `material_id`, из которого можно вывести `electroplating_family`;
- `quantity`;
- `coating_thickness_microns` для процессов осаждения/анодирования, если нужно переопределить дефолт, по текущей бизнес-настройке не влияет на трудоёмкость;
- `processing_depth_microns` для процессов съёма материала, если нужно переопределить дефолт.

## Путь от запроса до ответа

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` проверяет, что `electroplating_auto` входит в `AUTO_SERVICES`.
3. `main.py` требует `file_data` или `features_dict`, потому что расчёт зависит от площади, объёма и OBB-размеров.
4. Выполняется `validate_calculation_request`:
   - проверяется `service_id`;
   - проверяется `electroplating_process_id` или `cover_id[0]`;
   - проверяется `electroplating_family`;
   - если одновременно переданы `electroplating_family` и `material_id`, они должны соответствовать друг другу;
   - проверяется совместимость family/process;
   - проверяются неотрицательные `coating_thickness_microns` и `processing_depth_microns`;
   - `stl` отклоняется для electroplating_auto.
5. Если передан файл, `ParameterExtractor` выбирает `STPExtractor`.
6. `STPExtractor` извлекает `surface_area` в мм², `volume` в мм³ и OBB-размеры в мм.
7. Признаки кладутся в `merged_params["ml_features"]`. Название `ml_features` используется как общий контейнер геометрии; сам расчёт гальваники rule-based.
8. `SafeguardManager` подставляет только `material_form` и `location`, если они отсутствуют.
9. `CalculationRouter.should_use_ml` возвращает `False`.
10. `CalculationRouter._create_request` создаёт `ElectroplatingCalculationRequest`.
11. `ElectroplatingAutoCalculator.calculate` вызывает `calculate_electroplating_parameters`.
12. `calculate_electroplating_parameters`:
    - определяет операцию через `resolve_electroplating_process`;
    - определяет семейство материала через `resolve_material_family_for_electroplating`;
    - проверяет совместимость процесса и семейства;
    - переводит площадь `mm² -> dm²` и объём `mm³ -> dm³`;
    - считает массу детали по плотности семейства;
    - выбирает число работников по нормам массы;
    - считает загрузку ванны через `calculate_bath_layout`;
    - сначала всегда пробует обычную плоскостную раскладку с `clearance`, включая `quantity=1`;
    - если обычная раскладка с `clearance` даёт ненулевую вместимость, использует её как `batch_quantity` независимо от количества в заказе;
    - если плоскостная раскладка с `clearance` даёт нулевую вместимость, а одна деталь физически помещается в ванну без `clearance`, расчёт переходит в single-part fallback;
    - в single-part fallback используется `batch_quantity=1`, а `batch_count=requested_quantity`;
    - модель загрузки представляет деталь как подвес на плоскости, а не как 3D box packing;
    - рабочая плоскость берётся по первым двум размерам ванны;
    - у детали два максимальных OBB-габарита считаются проекцией на подвесную плоскость;
    - минимальный OBB-габарит считается глубиной/толщиной и проверяется по третьему размеру ванны;
    - допускается только поворот детали в подвесной плоскости на 90°, без произвольного 3D-поворота;
    - определяет `geometric_capacity` как идеальную вместимость подвесной плоскости;
    - определяет `practical_geometric_capacity` как технологически заниженную вместимость подвесной плоскости с коэффициентом;
    - определяет `batch_capacity` с учётом `practical_geometric_capacity`, тока и массы;
    - использует `batch_quantity = batch_capacity` как `n` в формуле трудоёмкости `(operation_coef * x) / n + z * k`;
    - сохраняет `requested_quantity` отдельно и использует его только как множитель итоговой трудоёмкости/стоимости заказа;
    - считает `batch_count` только как справочное число физических загрузок ванны;
    - считает операционную часть времени процесса по модели `fixed_time`, `faraday_deposition`, `faraday_layer_growth` или `faraday_material_removal`;
    - применяет runtime-переключатели из `ELECTROPLATING_TIME_MODEL_CONFIG`;
    - при `use_fixed_operation_time_by_process=False` значения из `ELECTROPLATING_FIXED_OPERATION_TIME_MIN_BY_PROCESS` остаются в конфиге, но дают `0` минут;
    - при `use_thickness_dependent_operation_time=False` толщина покрытия/слоя остаётся в параметрах, но не добавляет Faraday-время;
    - добавляет подготовительное время;
    - считает трудоёмкость одной детали и трудоёмкость заказа.
13. `ElectroplatingAutoCalculator` переводит трудоёмкость одной детали в стоимость через `COST_STRUCTURE[location]["price_of_hour"]` и `calculate_cost`, затем умножает цену на `quantity`.
14. Материальная часть ванны сейчас не добавляется: `mat_price = 0.0`.
15. В ответе `total_time` для `electroplating_auto` — трудоёмкость всего заказа; `work_time` и `work_time_per_part` в breakdown — трудоёмкость одной детали.
16. Ответ включает batch-поля: `batch_quantity`, `bath_batch_capacity`, `bath_geometric_capacity`, `bath_practical_geometric_capacity`, `bath_current_capacity`, `bath_weight_capacity`, `batch_count`, `batch_quantity_limited_by`.
17. `main.py` выставляет `calculation_engine="rule_based"` и возвращает success response.

## Пример payload

```json
{
  "service_id": "electroplating_auto",
  "electroplating_process_id": "galvanization_zinc_phosphating",
  "electroplating_family": "carbon_steel",
  "coating_thickness_microns": 9.0,
  "file_data": "<base64>",
  "file_name": "part.stp",
  "file_type": "stp",
  "quantity": 1,
  "location": "location_1"
}
```

## Основные файлы

- `main.py`
- `models/calculation_models.py::ElectroplatingCalculationRequest`
- `utils/electroplating_config.py`
- `calculations/electroplating.py`
- `calculators/electroplating_calculator.py`
- `extractors/stp_extractor.py`

## Из чего складывается трудоёмкость

В `calculations/electroplating.py` используется формула:

```text
labor_per_part_min = (ELECTROPLATING_LABOR_TIME_COEF * operation_time_min) / batch_quantity
                     + workers_count * mount_unmount_time_min
```

Где:

- `operation_time_min = preparation_time_min + coating_time_min`;
- `preparation_time_min` берётся из `ELECTROPLATING_PREPARATION_TIME_MIN_BY_PROCESS` или дефолта;
- `coating_time_min` — операционная часть процесса;
- `batch_quantity` — максимальное практическое количество деталей в одной загрузке ванны;
- `workers_count` определяется по массе детали;
- `mount_unmount_time_min` берётся из `ELECTROPLATING_DEFAULTS`.

Правило выбора `batch_quantity`:

- если обычная раскладка с `clearance` проходит, `batch_quantity` равен максимальной практической вместимости ванны. Это верно и для `quantity=1`;
- если обычная раскладка с `clearance` не проходит, но одна деталь помещается без `clearance`, используется single-part fallback: детали обрабатываются по одной, `batch_quantity=1`, `batch_count=quantity`.

Итоговая трудоёмкость заказа:

```text
order_labor_time_min = labor_per_part_min * requested_quantity
```

По текущей бизнес-настройке:

- `ELECTROPLATING_TIME_MODEL_CONFIG["use_fixed_operation_time_by_process"] = False`;
- `ELECTROPLATING_TIME_MODEL_CONFIG["use_thickness_dependent_operation_time"] = False`;
- поэтому `coating_time_min` для fixed-time словаря и для толщинных Faraday-процессов равен `0`;
- трудоёмкость складывается из подготовительного времени, распределённого на `batch_quantity`, и монтажа/демонтажа каждой детали.
