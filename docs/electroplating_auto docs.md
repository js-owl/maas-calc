# Рекомендуемый flow для фронта:

1. GET /operations_available?service_id=electroplating_auto
   -> получить список операций гальваники

2. GET /materials?process=electroplating_auto&electroplating_process_id=galvanization_zinc_phosphating
   -> получить материалы, доступные для выбранной операции

3. GET /material_forms?service_id=electroplating_auto&electroplating_process_id=galvanization_zinc_phosphating&material_id=steel_30XGSA
   -> получить формы выбранного материала

4. POST /calculate-price
   -> отправить расчётный запрос

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
  "material_id": "steel_30XGSA",
  "material_form": "sheet"
}