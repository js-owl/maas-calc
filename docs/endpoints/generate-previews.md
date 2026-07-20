# `POST /generate-previews`

## Назначение

Генерирует PNG-превью для CAD-файла и возвращает изображения в base64. Эндпойнт не сохраняет превью на диск как постоянный результат; сохранение должно выполнять вызывающее приложение.

## Вход

Multipart form-data:

- `file`: файл `.stl`, `.stp` или `.step`;
- `size`: размер квадратного PNG, по умолчанию `512`, допустимо `64..2048`;
- `views`: количество видов, по умолчанию `1`, допустимо `1..4`.

## Путь выполнения

1. Запрос попадает в `main.py::generate_previews`.
2. Расширение файла проверяется по `PREVIEW_SUPPORTED_EXT` из `utils/generate_previews.py`.
3. Файл читается в bytes.
4. Если файл пустой, возвращается calculation error.
5. `generate_preview_images_sync` запускается через `run_in_threadpool`.
6. Если генератор не смог отрендерить модель, используется PNG-заглушка `png_placeholder`.
7. PNG-байты кодируются в base64 через `b64`.
8. Ответ возвращается через `ResponseWrapper.success_response`.

## Ответ

`data` содержит:

- `filename`;
- `ext`;
- `size`;
- `views`;
- `images_png_base64`.

## Файлы

- `main.py`
- `utils/generate_previews.py`
- `utils/response_utils.py`
