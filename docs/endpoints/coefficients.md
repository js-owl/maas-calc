# `GET /coefficients`

## Назначение

Возвращает справочники коэффициентов и параметров, используемых фронтом для селекторов.

## Путь выполнения

1. Запрос попадает в `main.py::list_coefficients`.
2. Из `constants.py` читаются:
   - `TOLERANCE`;
   - `FINISH`;
   - `COVER`;
   - `CONTROL_TYPES`;
   - `CERT_COSTS`.
3. Из `utils.electroplating_config` читаются:
   - `get_process_params()`;
   - `get_baths()`.
4. Ответ возвращается через `ResponseWrapper.success_response`.

## Ответ

`data` содержит массивы:

- `tolerance`;
- `finish`;
- `cover`;
- `control_types`;
- `cert_costs`;
- `electroplating_processes`;
- `electroplating_baths`.

## Файлы

- `main.py`
- `constants.py`
- `utils/electroplating_config.py`
