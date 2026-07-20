# Рекомендуемый flow для фронта:

1. GET /operations_available?service_id=electroplating_auto
   -> получить список операций гальваники

2. GET /materials?process=electroplating_auto&electroplating_process_id=galvanization_zinc_phosphating
   -> получить материалы, доступные для выбранной операции

3. GET /material_forms?service_id=electroplating_auto&electroplating_process_id=galvanization_zinc_phosphating&material_id=steel_30XGSA
   -> получить формы выбранного материала

4. POST /calculate-price
   -> отправить расчётный запрос

Важно по трудоёмкости:

- `n` в формуле `(operation_coef * x) / n + z * k` — это максимальное количество таких деталей, помещающихся в одну ванну;
- обычная раскладка с `clearance` проверяется всегда, включая `quantity=1`;
- если обычная раскладка проходит, `n` равен максимальной практической вместимости ванны, даже когда в заказе одна деталь;
- если с `clearance` раскладка не помещает ни одной детали, но одна деталь физически помещается без `clearance`, детали считаются по одной за загрузку: `n=1`, `batch_count=quantity`;
- загрузка ванны считается не как плотная 3D-укладка, а как подвес деталей на плоскости;
- рабочая плоскость берётся по первым двум размерам ванны;
- у детали два максимальных OBB-габарита занимают подвесную плоскость;
- минимальный OBB-габарит считается глубиной/толщиной и должен помещаться в третий размер ванны;
- перебор ориентаций ограничен поворотом детали на 90° в подвесной плоскости;
- `geometric_capacity` — идеальная вместимость подвесной плоскости;
- `practical_geometric_capacity` — технологически заниженная вместимость с коэффициентом, именно она участвует в расчёте `batch_capacity`;
- `quantity` из запроса не подставляется вместо `n`;
- итоговая трудоёмкость заказа считается как трудоёмкость одной детали, умноженная на `quantity`;
- `batch_count` остаётся справочным числом физических загрузок ванны.
- `operation_time_min = preparation_time_min + coating_time_min`;
- по текущей бизнес-настройке `coating_time_min` не зависит от толщины покрытия;
- значения из `ELECTROPLATING_FIXED_OPERATION_TIME_MIN_BY_PROCESS` не удалены, но выключены конфигом и дают `0` минут;
- оба поведения управляются через `ELECTROPLATING_TIME_MODEL_CONFIG` в `utils/electroplating_config.py`.

Пример расчётного payload после выбора:
{
  "service_id": "electroplating_auto",
  "electroplating_process_id": "galvanization_zinc_phosphating",
  "coating_thickness_microns": 9.0,
  "file_data": "<base64>",
  "k_otk": 1.0,
  "quantity": 1,
  "location": "location_1",
  "file_type": "stp",
  "material_id": "steel_40Х13",
  "material_form": "sheet"
}
