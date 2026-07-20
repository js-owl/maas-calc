# `GET /other_services`

## Назначение

Возвращает сервисы, которые принимаются через `/calculate-price` как заявки на ручную оценку. Для них автоматическая цена равна `0` по бизнес-логике.

## Путь выполнения

1. Запрос попадает в `main.py::list_other_services`.
2. Код преобразует `constants.OTHER_SERVICES` в список объектов `{id, label, service}`.
3. Ответ возвращается через `ResponseWrapper.success_response`.

## Текущий список

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

## Файлы

- `main.py`
- `constants.py`
