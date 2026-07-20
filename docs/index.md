# Документация MaaS Backend STL

Документация описывает фактический runtime текущего проекта: какие эндпойнты доступны, какие `service_id` проходят автоматический расчёт, какие сервисы принимаются как ручная оценка, как работают валидации, safeguards и извлечение признаков из CAD-файлов.

## Разделы

### Эндпойнты

- [`GET /`](endpoints/root.md)
- [`GET /health`](endpoints/health.md)
- [`GET /version`](endpoints/version.md)
- [`POST /calculate-price`](endpoints/calculate-price.md)
- [`POST /generate-previews`](endpoints/generate-previews.md)
- [`GET /electroplating_material_families`](endpoints/electroplating-material-families.md)
- [`GET /materials`](endpoints/materials.md)
- [`GET /material_forms`](endpoints/material-forms.md)
- [`GET /services`](endpoints/services.md)
- [`GET /auto_services`](endpoints/auto-services.md)
- [`GET /other_services`](endpoints/other-services.md)
- [`GET /all_services`](endpoints/all-services.md)
- [`GET /coefficients`](endpoints/coefficients.md)
- [`GET /locations`](endpoints/locations.md)
- [`GET /operations_available`](endpoints/operations-available.md)

### `service_id`

Автоматический расчёт:

- [`printing`](service_ids/printing.md)
- [`cnc-milling`](service_ids/cnc-milling.md)
- [`composite`](service_ids/composite.md)
- [`electroplating_auto`](service_ids/electroplating_auto.md)

Ручная оценка через `/calculate-price`, успешный ответ с ценой `0`:

- [`bending`](service_ids/bending.md)
- [`handing`](service_ids/handing.md)
- [`heating`](service_ids/heating.md)
- [`laser-cutting`](service_ids/laser-cutting.md)
- [`grinding`](service_ids/grinding.md)
- [`welding`](service_ids/welding.md)
- [`casting`](service_ids/casting.md)
- [`other`](service_ids/other.md)
- [`testing`](service_ids/testing.md)
- [`rubber`](service_ids/rubber.md)

Конфигурационный неавтоматический service id:

- [`electroplating`](service_ids/electroplating.md)

### Внутренняя логика

- [Маршрутизация расчёта](internals/calculation-routing.md)
- [Валидации](internals/validations.md)
- [Safeguards](internals/safeguards.md)
- [Бизнес-константы](internals/business-constants.md)
- [Стандарт ответа](internals/response-wrapper.md)
- [Стандарт структуры цены](internals/unified-pricing.md)
- [Materials price sync (backend + stl)](internals/materials-price-sync.md)

### Экстракторы

- [`ParameterExtractor`](extractors/parameter_extractor.md)
- [`FileParameterExtractor`](extractors/file_extractor.md)
- [`STLExtractor`](extractors/stl_extractor.md)
- [`STPExtractor`](extractors/stp_extractor.md)
