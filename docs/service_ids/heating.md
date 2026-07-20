# `service_id="heating"`

## Назначение

`Термическая обработка`. Этот service id относится к `constants.OTHER_SERVICES` и принимается через `/calculate-price` как заявка на ручную оценку производством.

## Путь от запроса до ответа

1. Запрос приходит в `POST /calculate-price`.
2. `main.py` собирает `OTHER_SERVICES_LIST` из `constants.OTHER_SERVICES`.
3. Так как `service_id="heating"` находится в `OTHER_SERVICES_LIST`, endpoint сразу формирует `UnifiedCalculationResponse`.
4. Поля цены и времени выставляются в `0`:
   - `part_price=0`;
   - `detail_price=0`;
   - `part_price_one=0`;
   - `detail_price_one=0`;
   - `total_price=0`;
   - `total_time=0`.
5. `calculation_method` выставляется в `manual_pricing`.
6. Файловая экстракция, автоматические валидации, safeguards и `CalculationRouter` не запускаются.
7. Ответ возвращается через `ResponseWrapper.success_response`.

## Почему цена равна нулю

Нулевая цена здесь не означает бесплатное изготовление. Это технический успешный ответ: стоимость будет оцениваться людьми на производстве после создания заявки.

## Основные файлы

- `main.py`
- `constants.py::OTHER_SERVICES`
- `models/response_models.py::UnifiedCalculationResponse`
