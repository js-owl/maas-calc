# `STPExtractor`

## Файл

`extractors/stp_extractor.py`.

## Назначение

Извлекает геометрию и набор ML/B-Rep признаков из STP/STEP через CADQuery и OCP.

## Когда используется

`ParameterExtractor` выбирает `STPExtractor`, если `file_type` равен `stp` или `step`.

## Путь выполнения

1. `extract_parameters` сохраняет base64-файл во временный файл.
2. Вызывает `_analyze_stp_file`.
3. `_analyze_stp_file` импортирует модель через `cadquery.importers.importStep`.
4. Берёт `shape.val()`.
5. Считает:
   - объём через `shape_val.Volume()`;
   - площадь через `shape_val.Area()` или сумму площадей solids;
   - OBB через `Bnd_OBB` и `BRepBndLib.AddOBB_s`.
6. Из OBB формируются:
   - `obb_x`, `obb_y`, `obb_z`;
   - `dimensions`;
   - `min_size`, `mid_size`, `max_size`;
   - `bbox_volume`;
   - `volume_bar`;
   - `surface_area_obb`.
7. Из topological entities берутся faces, edges, vertices, wires.
8. Считаются face metrics:
   - количество плоскостей, цилиндров, конусов, торов, сфер, bspline;
   - entropy по типам поверхностей;
   - площади по типам поверхностей;
   - доли площадей;
   - количество уникальных нормалей плоских граней.
9. Считаются edge metrics:
   - число straight/curved/circle/bspline edges;
   - entropy по типам рёбер;
   - длины по типам;
   - доли длин.
10. Считаются derived metrics:
    - `surface_to_volume_ratio`;
    - `obb_compactness`;
    - `sphericity`;
    - `topology_complexity_score`;
    - `removable_score`;
    - `removable_score_better`;
    - `surface_area_detail_obb_ratio`;
    - `removable_volume`.
11. Если CADQuery-анализ падает, возвращается `_basic_stp_analysis` с нулевыми/пустыми признаками.
12. Временный файл удаляется в `finally`.

## Выходные поля

STP extractor возвращает широкий плоский словарь признаков. Ключевые поля для текущих сервисов:

- `volume`;
- `surface_area`;
- `dimensions`;
- `obb_x`, `obb_y`, `obb_z`;
- `min_size`, `mid_size`, `max_size`;
- `bbox_volume`;
- `volume_bar`;
- `surface_area_obb`;
- topology/face/edge features.

## Использование в сервисах

- `cnc-milling` — признаки идут в ML labor model и classifier.
- `composite` — признаки идут в ML labor model и расчёт оснастки.
- `electroplating_auto` — используются `surface_area`, `volume`, OBB dimensions для rule-based расчёта ванны и трудоёмкости.
