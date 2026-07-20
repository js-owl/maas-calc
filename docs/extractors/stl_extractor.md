# `STLExtractor`

## Файл

`extractors/stl_extractor.py`.

## Назначение

Извлекает геометрию из STL через `trimesh`.

## Когда используется

`ParameterExtractor` выбирает `STLExtractor`, если `file_type="stl"`.

## Путь выполнения

1. `extract_parameters` сохраняет base64-файл во временный файл через `_save_temp_file`.
2. Вызывает `_analyze_stl_file`.
3. `_analyze_stl_file` загружает mesh через `trimesh.load`.
4. Из mesh берутся:
   - `mesh.volume`;
   - `mesh.area`;
   - oriented bounding box через `mesh.bounding_box_oriented`.
5. OBB extents сортируются:
   - `obb_x` — максимальный размер;
   - `obb_y` — средний размер;
   - `obb_z` — минимальный размер.
6. Формируется `dimensions = {length, width, height}`.
7. Считаются aspect ratios, `bbox_volume`, `min_size`, `mid_size`, `max_size`.
8. `_extract_stl_surface_features` возвращает простые mesh-метрики:
   - `face_count`;
   - `vertex_count`;
   - `edge_count`.
9. Временный файл удаляется в `finally`.

## Выходные поля

- `dimensions`;
- `volume`;
- `surface_area`;
- `features`;
- `obb_x`, `obb_y`, `obb_z`;
- `min_size`, `mid_size`, `max_size`;
- `aspect_ratio_xy`, `aspect_ratio_yz`, `aspect_ratio_xz`;
- `bbox_volume`;
- `check_sizes_for_lathe`;
- `file_info`.

## Ограничения

STL не используется для `cnc-milling`, `composite` и `electroplating_auto` по текущей валидации. Для этих сервисов нужен B-Rep/STEP-контур.
