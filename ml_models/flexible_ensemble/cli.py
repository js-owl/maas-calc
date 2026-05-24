from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from .autobrep_fsq import AutoBrepFSQRuntimeConfig, merge_autobrep_fsq_features_into_frames
from .config import BinMetricConfig, BusinessLossConfig, EnsembleConfig, FeatureSpec, ModelFlags, GNNConfig, GNNOptunaConfig
from .complexity_classifier import run_complexity_classifier_experiments
from .suspicious import (
    build_repeated_oof_seeds,
    parse_model_groups_json,
    run_repeated_oof_suspicious_analysis,
)
from .trainer import FlexibleRegressorEnsemble
from .utils import (
    _build_segment_metrics_from_pred_df,
    _collect_feature_importances,
    _collect_optuna_trials_metrics,
    _evaluate_predictions,
    _infer_numeric_features,
    _load_dataframe,
    _parse_csv_list,
    _parse_float_list,
    _parse_int_float_dict,
    _parse_json_dict,
    _resolve_eval_target_col,
    _summary_to_df,
    _write_results_workbook,
)


def _parse_bool_csv(value: str) -> list[bool]:
    items = _parse_csv_list(value)
    if not items:
        return []
    mapping = {
        "1": True,
        "0": False,
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
        "y": True,
        "n": False,
    }
    out: list[bool] = []
    for item in items:
        key = str(item).strip().lower()
        if key not in mapping:
            raise ValueError(f"Не удалось распарсить bool-список: {item}")
        out.append(mapping[key])
    return out


def _validate_required_columns(
    df: pd.DataFrame,
    required: list[str],
    *,
    df_name: str,
    context: str,
) -> None:
    normalized = [str(col) for col in required if col]
    missing = [col for col in dict.fromkeys(normalized) if col not in df.columns]
    if missing:
        raise ValueError(
            f"В {df_name} отсутствуют колонки для режима '{context}': {missing}"
        )


def _validate_test_dataframe_columns(
    test_df: Optional[pd.DataFrame],
    *,
    feature_spec: FeatureSpec,
    group_col: Optional[str],
    balance_columns: list[str],
    gnn_enabled: bool,
    gnn_part_key_col: Optional[str],
    explicit_test_target_col: Optional[str],
    fallback_target_col: str,
    optuna_test_score_weight: float,
    complexity_clf_enabled: bool,
) -> None:
    if test_df is None:
        return

    inference_required = (
        list(feature_spec.numeric_features)
        + list(feature_spec.categorical_features)
        + list(feature_spec.embedding_features)
    )
    if gnn_enabled:
        if not gnn_part_key_col:
            raise ValueError("Включён GNN, но не задан --gnn-part-key-col")
        inference_required.append(gnn_part_key_col)

    _validate_required_columns(
        test_df,
        inference_required,
        df_name="test_df",
        context="predict/test inference",
    )

    # Если пользователь явно указал test-target-col, проверяем его сразу,
    # чтобы режимы eval не отключались молча.
    if explicit_test_target_col:
        _validate_required_columns(
            test_df,
            [explicit_test_target_col],
            df_name="test_df",
            context="test evaluation (--test-target-col)",
        )

    if optuna_test_score_weight > 0.0:
        eval_target_col = _resolve_eval_target_col(
            test_df,
            explicit_test_target_col,
            fallback_target_col,
        )
        if eval_target_col is None:
            expected_col = explicit_test_target_col or fallback_target_col
            raise ValueError(
                "optuna_test_score_weight > 0, но в test_df не найден target-col "
                f"для оценки: {expected_col}"
            )

    # complexity classifier умеет работать и без target на test,
    # но feature-колонки для inference должны быть валидны.
    if complexity_clf_enabled:
        _validate_required_columns(
            test_df,
            inference_required,
            df_name="test_df",
            context="complexity classifier test inference",
        )

    # Эти колонки не обязательны, но если пользователь ожидает сегментные
    # срезы по ним на test, лучше подсветить отсутствие заранее.
    optional_report_cols = [c for c in list(dict.fromkeys(([group_col] if group_col else []) + balance_columns)) if c]
    missing_optional = [c for c in optional_report_cols if c not in test_df.columns]
    if missing_optional:
        print(
            "Warning: в test_df отсутствуют колонки для segment/balance slicing:",
            missing_optional,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Flexible ensemble regressor trainer")

    # input / output
    p.add_argument("--input-path", required=True)
    p.add_argument("--target-col", required=True)
    p.add_argument("--group-col", default=None)
    p.add_argument("--suffix", default="run")
    p.add_argument("--output-dir", default=".")
    p.add_argument("--dropna", action="store_true")
    p.add_argument("--filter-query", default=None)

    # features
    p.add_argument("--numeric-features", default=None, help="CSV-список numeric columns или auto")
    p.add_argument("--categorical-features", default="")
    p.add_argument("--embedding-features", default="")
    p.add_argument("--catboost-embedding-features", default="", help="CSV-список embedding-колонок, которые подавать в CatBoost нативно через embedding_features")

    # AutoBrep FSQ features
    p.add_argument("--autobrep-fsq-features-path", default=None, help="Готовый parquet/csv/xlsx с AutoBrep FSQ-признаками")
    p.add_argument("--autobrep-fsq-cache-path", default=None, help="Куда сохранить/откуда читать закэшированную таблицу AutoBrep FSQ-признаков")
    p.add_argument("--autobrep-fsq-npz-dir", default=None, help="Папка с AutoBrep point-grid .npz файлами по деталям")
    p.add_argument("--autobrep-fsq-merge-col", default=None, help="Колонка train/test df для стыковки с AutoBrep-признаками, например filename")
    p.add_argument("--autobrep-surf-ckpt", default=None, help="Путь к surf-fsq.ckpt")
    p.add_argument("--autobrep-edge-ckpt", default=None, help="Путь к edge-fsq.ckpt")
    p.add_argument("--autobrep-ar-ckpt", default=None, help="Путь к autoregressive ar.ckpt для полного кодирования детали")
    p.add_argument("--autobrep-fsq-device", default=None, help="cuda / cpu; по умолчанию auto")
    p.add_argument("--autobrep-fsq-batch-size", type=int, default=128)
    p.add_argument("--autobrep-fsq-key-mode", choices=["exact", "basename", "stem", "lower", "lower_basename", "lower_stem"], default="stem")
    p.add_argument("--autobrep-fsq-strict", action=argparse.BooleanOptionalAction, default=True, help="Падать, если для части деталей не удалось собрать AutoBrep-признаки")
    p.add_argument("--autobrep-fsq-add-surface-emb", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--autobrep-fsq-add-edge-emb", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--autobrep-fsq-add-combined-emb", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--autobrep-fsq-add-cad-emb", action=argparse.BooleanOptionalAction, default=False, help="Добавить pooled embedding полной CAD-последовательности через AutoBrep AR")
    p.add_argument("--autobrep-cad-window-stride", type=int, default=None, help="Шаг окна по токенам для длинных CAD-последовательностей; по умолчанию равен max_seq из ar.ckpt")
    p.add_argument("--autobrep-fsq-add-numeric-meta", action=argparse.BooleanOptionalAction, default=True)

    # split balancing
    p.add_argument("--balance-columns", default="", help="CSV-список столбцов для выравнивания пропорций внутри target-бинов")
    p.add_argument("--balance-min-count", type=int, default=None)
    p.add_argument("--balance-fillna-value", default="__MISSING__")
    p.add_argument("--balance-rare-value", default="__RARE__")

    # model flags / registry
    p.add_argument("--models", default="", help="Полный CSV-список моделей ансамбля. Если задан, переопределяет флаги disable-* и extra-models. Пример: ridge,svr,lgbm,xgb")
    p.add_argument("--extra-models", default="", help="Дополнительные модели к стандартному набору. Пример: ridge,svr")
    p.add_argument("--disable-mlp", action="store_true")
    p.add_argument("--disable-lgbm", action="store_true")
    p.add_argument("--disable-catboost", action="store_true")
    p.add_argument("--disable-xgb", action="store_true")
    p.add_argument("--disable-rf", action="store_true")
    p.add_argument("--enable-gnn", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--gnn-dataset-dir", default=None, help="Папка train graphs.pt + feature_spec.json для GNN")
    p.add_argument("--gnn-inference-dataset-dir", default=None, help="Папка inference/test graphs.pt для GNN predict на внешнем наборе")
    p.add_argument("--gnn-part-key-col", default=None, help="Колонка part_key / filename для стыковки строк таблицы с графами")
    p.add_argument("--gnn-device", default=None, help="cuda / cpu; по умолчанию auto")
    p.add_argument("--gnn-hidden-dim", type=int, default=96)
    p.add_argument("--gnn-num-layers", type=int, default=4)
    p.add_argument("--gnn-dropout", type=float, default=0.15)
    p.add_argument("--gnn-train-eps", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--gnn-epochs", type=int, default=300)
    p.add_argument("--gnn-batch-size", type=int, default=24)
    p.add_argument("--gnn-eval-batch-size", type=int, default=64)
    p.add_argument("--gnn-lr", type=float, default=1e-3)
    p.add_argument("--gnn-weight-decay", type=float, default=1e-4)
    p.add_argument("--gnn-loss", choices=["huber", "mse", "l1"], default="huber")
    p.add_argument("--gnn-monitor-metric", choices=["rmse", "mae", "rmsle", "mape_pct", "wape_pct"], default="rmsle")
    p.add_argument("--gnn-lr-factor", type=float, default=0.5)
    p.add_argument("--gnn-lr-patience", type=int, default=12)
    p.add_argument("--gnn-early-stopping-patience", type=int, default=30)
    p.add_argument("--gnn-min-delta", type=float, default=1e-5)
    p.add_argument("--gnn-prediction-cap-multiplier", type=float, default=2.0, help="Верхний cap предсказания GNN как множитель от max(y_train) fold/full-fit")
    p.add_argument("--gnn-grad-clip-norm", type=float, default=1.0, help="gradient clipping norm для GNN; <=0 отключает")
    p.add_argument("--gnn-weighted-loss-enabled", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--gnn-weighted-loss-bins", type=int, default=5)
    p.add_argument("--gnn-weighted-loss-power", type=float, default=0.5)
    p.add_argument("--gnn-weighted-loss-max-weight", type=float, default=5.0)
    p.add_argument("--gnn-weighted-sampler-enabled", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--gnn-weighted-sampler-power", type=float, default=0.5)
    p.add_argument("--gnn-weighted-sampler-max-weight", type=float, default=5.0)
    p.add_argument("--gnn-optuna-enabled", action=argparse.BooleanOptionalAction, default=True, help="Включить отдельный search-space Optuna для GNN внутри общего optuna-контура")
    p.add_argument("--gnn-optuna-epochs", type=int, default=120, help="epochs override только для Optuna trial GNN")
    p.add_argument("--gnn-optuna-early-stopping-patience", type=int, default=20, help="early stopping patience override только для Optuna trial GNN")
    p.add_argument("--gnn-optuna-eval-batch-size", type=int, default=None, help="eval_batch_size override только для Optuna trial GNN")
    p.add_argument("--gnn-optuna-min-delta", type=float, default=None, help="min_delta override только для Optuna trial GNN")
    p.add_argument("--gnn-optuna-hidden-dims", default="64,96,128")
    p.add_argument("--gnn-optuna-num-layers", default="3,4")
    p.add_argument("--gnn-optuna-dropout-min", type=float, default=0.10)
    p.add_argument("--gnn-optuna-dropout-max", type=float, default=0.30)
    p.add_argument("--gnn-optuna-lr-min", type=float, default=3e-4)
    p.add_argument("--gnn-optuna-lr-max", type=float, default=1e-3)
    p.add_argument("--gnn-optuna-weight-decay-min", type=float, default=1e-5)
    p.add_argument("--gnn-optuna-weight-decay-max", type=float, default=1e-3)
    p.add_argument("--gnn-optuna-batch-sizes", default="16,24,32")
    p.add_argument("--gnn-optuna-losses", default="huber,l1")
    p.add_argument("--gnn-optuna-train-eps", default="false", help="CSV-список булевых значений для Optuna GNN, например false,true")
    p.add_argument("--gnn-optuna-reject-on-nonfinite", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--gnn-optuna-reject-score-value", type=float, default=1e9)
    p.add_argument("--gnn-optuna-reject-pred-above-train-multiplier", type=float, default=3.0)
    p.add_argument("--gnn-optuna-reject-train-cv-ratio", type=float, default=20.0)

    # ensemble config
    p.add_argument("--n-splits", type=int, default=5)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--stratify-target-bins", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--n-target-bins", type=int, default=5, help="Число target-бинов только для split/stratification")

    p.add_argument("--use-optuna", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--optuna-trials", type=int, default=25)
    p.add_argument("--optuna-timeout", type=int, default=None)
    p.add_argument("--optuna-n-splits", type=int, default=3)
    p.add_argument(
        "--optuna-objective-mode",
        choices=[
            "composite_optuna",
            "pct_error_sum",
            "pct_error_sum_tail",
            "pct_error_sum_bin_balanced",
            "metric_name"
        ],
        default="composite_optuna",
        help=(
            "Режим objective для Optuna: "
            "composite_optuna = старая логика; "
            "pct_error_sum = mean(pct_error_to_true + pct_error_to_pred); "
            "pct_error_sum_tail = mean + tail_weight * quantile; "
            "pct_error_sum_bin_balanced = среднее по бинам от pct_error_sum_mean"
        ),
    )

    p.add_argument("--ensemble-mode", choices=["weighted", "mean"], default="weighted")
    p.add_argument("--metric-name", choices=["rmse", "mae", "rmsle", "wape", "mape_smooth"], default="rmsle")
    p.add_argument(
        "--mape-smooth-alpha",
        type=float,
        default=10.0,
        help="alpha для mape_smooth/smape_smooth",
    )
    p.add_argument(
        "--pct-error-sum-tail-weight",
        type=float,
        default=0.30,
        help="вес хвостовой компоненты в pct_error_sum_tail",
    )
    p.add_argument(
        "--pct-error-sum-tail-quantile",
        type=float,
        default=0.90,
        help="квантиль хвоста для pct_error_sum_tail, например 0.90",
    )
    p.add_argument("--cv-score-mode", choices=["composite_optuna", "standard"], default="composite_optuna")
    p.add_argument("--optuna-test-score-weight", type=float, default=0.0, help="Вес test-score в Optuna objective: 0.0 = не использовать, 1.0 = только test-score")
    p.add_argument("--target-transform", choices=["none", "log", "log1p"], default="none", help="Преобразование target при обучении; метрики и предсказания остаются в исходной шкале")
    p.add_argument("--train-on-logy", action="store_true", help="Удобный флаг: эквивалент --target-transform log")
    p.add_argument("--final-fit-mode", choices=["full_refit", "fold_ensemble", "hybrid"], default="full_refit", help="Как строить финальные модели для predict(): один full refit, среднее по fold-моделям, или гибрид")
    p.add_argument("--hybrid-full-weight", type=float, default=0.5, help="Вес full-refit модели в hybrid-режиме; доля fold-ensemble = 1 - weight")
    p.add_argument("--custom-params-json", default="{}")

    # bin metric config
    p.add_argument("--bin-enabled", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--bin-strategy", choices=["fixed", "quantile"], default="fixed")
    p.add_argument("--bin-fixed-edges", default="0.5,1.0,2.0,5.0,10.0")
    p.add_argument("--bin-n-bins", type=int, default=6, help="Число бинов только для analysis/bin-report при --bin-strategy quantile")
    p.add_argument("--bin-min-size", type=int, default=5)
    p.add_argument("--bin-ape-floor", type=float, default=0.25)
    p.add_argument("--bin-weights-json", default="{}")
    p.add_argument("--bin-optuna-w-mean-rmsle", type=float, default=0.55)
    p.add_argument("--bin-optuna-w-std-rmsle", type=float, default=0.15)
    p.add_argument("--bin-optuna-w-mean-wape", type=float, default=0.20)
    p.add_argument("--bin-optuna-w-global-bias", type=float, default=0.10)

    # business loss config
    p.add_argument("--business-enabled", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--small-target-threshold", type=float, default=1.0)
    p.add_argument("--small-abs-error-limit", type=float, default=1.0)
    p.add_argument("--large-pct-error-to-true-limit", type=float, default=1.0)
    p.add_argument("--large-pct-error-to-pred-limit", type=float, default=1.0)
    p.add_argument("--business-denom-eps", type=float, default=1e-6)
    p.add_argument("--business-excess-power", type=float, default=2.0)
    p.add_argument("--business-optuna-existing-score-weight", type=float, default=0.65)
    p.add_argument("--business-optuna-score-weight", type=float, default=0.35)
    p.add_argument("--business-w-small-violation-rate", type=float, default=0.30)
    p.add_argument("--business-w-small-excess-mean", type=float, default=0.30)
    p.add_argument("--business-w-large-true-violation-rate", type=float, default=0.15)
    p.add_argument("--business-w-large-true-excess-mean", type=float, default=0.10)
    p.add_argument("--business-w-large-pred-violation-rate", type=float, default=0.10)
    p.add_argument("--business-w-large-pred-excess-mean", type=float, default=0.05)

    # test / inference output
    p.add_argument("--test-path", default=None)
    p.add_argument("--test-target-col", default=None)
    p.add_argument("--test-dropna", action="store_true")
    p.add_argument("--test-filter-query", default=None)

    # AutoBrep FSQ overrides for external test/inference set
    p.add_argument("--test-autobrep-fsq-features-path", default=None, help="Отдельный parquet/csv/xlsx с AutoBrep FSQ-признаками для test/inference набора")
    p.add_argument("--test-autobrep-fsq-cache-path", default=None, help="Отдельный cache path с AutoBrep FSQ-признаками для test/inference набора")
    p.add_argument("--test-autobrep-fsq-npz-dir", default=None, help="Отдельная папка с AutoBrep point-grid .npz файлами для test/inference набора")
    p.add_argument("--test-autobrep-fsq-merge-col", default=None, help="Колонка test df для стыковки с AutoBrep-признаками; по умолчанию используется --autobrep-fsq-merge-col")
    p.add_argument("--test-autobrep-surf-ckpt", default=None, help="Опциональный override пути к surf-fsq.ckpt для test/inference AutoBrep")
    p.add_argument("--test-autobrep-edge-ckpt", default=None, help="Опциональный override пути к edge-fsq.ckpt для test/inference AutoBrep")
    p.add_argument("--test-autobrep-ar-ckpt", default=None, help="Опциональный override пути к ar.ckpt для test/inference AutoBrep")
    p.add_argument("--test-autobrep-fsq-device", default=None, help="Опциональный override device для test/inference AutoBrep")
    p.add_argument("--test-autobrep-fsq-batch-size", type=int, default=None, help="Опциональный override batch size для test/inference AutoBrep")
    p.add_argument("--test-autobrep-fsq-key-mode", choices=["exact", "basename", "stem", "lower", "lower_basename", "lower_stem"], default=None, help="Опциональный override key mode для test/inference AutoBrep")

    # feature importances export
    p.add_argument("--feature-importance-models", default="ensemble,lgbm,catboost,xgb,rf")
    p.add_argument("--feature-importance-top-n", type=int, default=100)
    p.add_argument("--feature-importance-aggregate", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--feature-importance-normalize", action=argparse.BooleanOptionalAction, default=True)

    # suspicious objects / repeated OOF
    p.add_argument("--suspicious-analysis", action=argparse.BooleanOptionalAction, default=False, help="Запустить repeated OOF и собрать диагностику подозрительных объектов")
    p.add_argument("--suspicious-id-col", default=None, help="Колонка идентификатора детали для suspicious report; если не задана, используется row_id")
    p.add_argument("--suspicious-material-col", default="material_name_main", help="Колонка материала для neighbor consistency")
    p.add_argument("--suspicious-neighbors-k", type=int, default=5, help="Число соседей внутри материала для оценки согласованности target")
    p.add_argument("--suspicious-seeds", default="", help="CSV-список seed для repeated OOF; если пусто, генерируется 5 seed от --random-state")
    p.add_argument("--suspicious-model-groups-json", default="", help='JSON-объект групп моделей для repeated OOF, например {"linear":["ridge","elasticnet"],"kernel":["svr"],"bagging":["rf"],"boosting":["lgbm","xgb","catboost"]}')

    # bundle save / experimental complexity classifier
    p.add_argument("--save-bundle-path", default=None, help="Куда сохранить bundle для инференса: файл .joblib/.pkl или директория")
    p.add_argument("--complexity-clf-enabled", action=argparse.BooleanOptionalAction, default=False, help="Запустить экспериментальные бинарные классификаторы для правила y >= threshold")
    p.add_argument("--complexity-clf-threshold", type=float, default=1.0, help="Порог сложной детали: class=1, если y >= threshold")
    p.add_argument("--complexity-clf-models", default="catboost,lgbm,logreg", help="CSV-список моделей complexity classifier: catboost,lgbm,logreg")
    p.add_argument("--complexity-clf-prob-threshold", type=float, default=0.5, help="Порог вероятности для precision/recall/F1/confusion")
    p.add_argument("--complexity-clf-threshold-grid", default="", help="CSV-список вероятностных порогов для таблицы precision/recall/F1; если пусто, используется стандартная сетка 0.05..0.95")

    # consolidated workbook
    p.add_argument("--report-file", default=None)

    return p

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    train_df = _load_dataframe(args.input_path)

    if args.dropna:
        train_df = train_df.dropna()
    if args.filter_query:
        train_df = train_df.query(args.filter_query)

    train_df = train_df.reset_index(drop=True)

    test_df: Optional[pd.DataFrame] = None
    if args.test_path:
        test_df = _load_dataframe(args.test_path)
        if args.test_dropna:
            test_df = test_df.dropna()
        if args.test_filter_query:
            test_df = test_df.query(args.test_filter_query)
        test_df = test_df.reset_index(drop=True)

    categorical_features = _parse_csv_list(args.categorical_features)
    embedding_features = _parse_csv_list(args.embedding_features)
    catboost_embedding_features = _parse_csv_list(args.catboost_embedding_features)
    balance_columns = _parse_csv_list(args.balance_columns)
    fi_models = _parse_csv_list(args.feature_importance_models)
    models_override = _parse_csv_list(args.models)
    extra_models = _parse_csv_list(args.extra_models)

    autobrep_embedding_cols: list[str] = []
    autobrep_numeric_cols: list[str] = []
    autobrep_features_table: pd.DataFrame = pd.DataFrame()
    base_autobrep_enabled = any([
        args.autobrep_fsq_features_path,
        args.autobrep_fsq_cache_path,
        args.autobrep_fsq_npz_dir,
    ])
    test_autobrep_enabled = any([
        args.test_autobrep_fsq_features_path,
        args.test_autobrep_fsq_cache_path,
        args.test_autobrep_fsq_npz_dir,
    ])
    if base_autobrep_enabled or test_autobrep_enabled:
        if not args.autobrep_fsq_merge_col:
            raise ValueError("Для AutoBrep FSQ нужно задать --autobrep-fsq-merge-col")
        if test_autobrep_enabled and test_df is None:
            raise ValueError("Заданы test AutoBrep FSQ args, но отсутствует --test-path")
        if test_autobrep_enabled and test_df is not None:
            _validate_required_columns(
                test_df,
                [args.test_autobrep_fsq_merge_col or args.autobrep_fsq_merge_col],
                df_name="test_df",
                context="AutoBrep FSQ merge",
            )
        autobrep_cfg = AutoBrepFSQRuntimeConfig(
            merge_col=args.autobrep_fsq_merge_col,
            npz_dir=args.autobrep_fsq_npz_dir,
            features_path=args.autobrep_fsq_features_path,
            cache_path=args.autobrep_fsq_cache_path,
            surf_ckpt=args.autobrep_surf_ckpt,
            edge_ckpt=args.autobrep_edge_ckpt,
            ar_ckpt=args.autobrep_ar_ckpt,
            device=args.autobrep_fsq_device,
            batch_size=args.autobrep_fsq_batch_size,
            key_mode=args.autobrep_fsq_key_mode,
            strict=args.autobrep_fsq_strict,
            add_surface_embedding=args.autobrep_fsq_add_surface_emb,
            add_edge_embedding=args.autobrep_fsq_add_edge_emb,
            add_combined_embedding=args.autobrep_fsq_add_combined_emb,
            add_cad_embedding=args.autobrep_fsq_add_cad_emb,
            add_numeric_meta=args.autobrep_fsq_add_numeric_meta,
            sequence_window_stride=args.autobrep_cad_window_stride,
        )

        test_autobrep_cfg: Optional[AutoBrepFSQRuntimeConfig] = None
        if test_autobrep_enabled:
            test_autobrep_cfg = AutoBrepFSQRuntimeConfig(
                merge_col=args.test_autobrep_fsq_merge_col or args.autobrep_fsq_merge_col,
                npz_dir=args.test_autobrep_fsq_npz_dir,
                features_path=args.test_autobrep_fsq_features_path,
                cache_path=args.test_autobrep_fsq_cache_path,
                surf_ckpt=args.test_autobrep_surf_ckpt or args.autobrep_surf_ckpt,
                edge_ckpt=args.test_autobrep_edge_ckpt or args.autobrep_edge_ckpt,
                ar_ckpt=args.test_autobrep_ar_ckpt or args.autobrep_ar_ckpt,
                device=args.test_autobrep_fsq_device or args.autobrep_fsq_device,
                batch_size=args.test_autobrep_fsq_batch_size or args.autobrep_fsq_batch_size,
                key_mode=args.test_autobrep_fsq_key_mode or args.autobrep_fsq_key_mode,
                strict=args.autobrep_fsq_strict,
                add_surface_embedding=args.autobrep_fsq_add_surface_emb,
                add_edge_embedding=args.autobrep_fsq_add_edge_emb,
                add_cad_embedding=args.autobrep_fsq_add_cad_emb,
                add_combined_embedding=args.autobrep_fsq_add_combined_emb,
                add_numeric_meta=args.autobrep_fsq_add_numeric_meta,
                sequence_window_stride=args.autobrep_cad_window_stride,
            )

        train_df, test_df, autobrep_embedding_cols, autobrep_numeric_cols, autobrep_features_table = (
            merge_autobrep_fsq_features_into_frames(
                train_df=train_df,
                test_df=test_df,
                cfg=autobrep_cfg,
                test_cfg=test_autobrep_cfg,
            )
        )
        embedding_features = list(dict.fromkeys(embedding_features + autobrep_embedding_cols))

    missing_catboost_emb = [c for c in catboost_embedding_features if c not in embedding_features]
    if missing_catboost_emb:
        raise ValueError(
            f"Колонки из --catboost-embedding-features отсутствуют в embedding_features: {missing_catboost_emb}"
        )
    
    if args.numeric_features is None or str(args.numeric_features).strip().lower() == "auto":
        excluded_extra = []
        if args.group_col:
            excluded_extra.append(args.group_col)
        excluded_extra.extend(balance_columns)

        numeric_features = _infer_numeric_features(
            df=train_df,
            target_col=args.target_col,
            categorical_features=categorical_features,
            embedding_features=embedding_features,
            excluded_extra=excluded_extra,
        )
    else:
        numeric_features = _parse_csv_list(args.numeric_features)

    if autobrep_numeric_cols:
        numeric_features = list(dict.fromkeys(numeric_features + autobrep_numeric_cols))

    feature_spec = FeatureSpec(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        embedding_features=embedding_features,
        catboost_embedding_features=catboost_embedding_features,
    )

    model_flags = ModelFlags(
        use_mlp=not args.disable_mlp,
        use_lgbm=not args.disable_lgbm,
        use_catboost=not args.disable_catboost,
        use_xgb=not args.disable_xgb,
        use_rf=not args.disable_rf,
        use_gnn=args.enable_gnn,
        extra_models=extra_models,
        models_override=models_override if models_override else None,
    )

    bin_metric_config = BinMetricConfig(
        enabled=args.bin_enabled,
        strategy=args.bin_strategy,
        fixed_edges=_parse_float_list(args.bin_fixed_edges),
        n_bins=args.bin_n_bins,
        min_bin_size=args.bin_min_size,
        ape_floor=args.bin_ape_floor,
        bin_weights=_parse_int_float_dict(args.bin_weights_json),
        optuna_w_mean_bin_rmsle=args.bin_optuna_w_mean_rmsle,
        optuna_w_std_bin_rmsle=args.bin_optuna_w_std_rmsle,
        optuna_w_mean_bin_wape=args.bin_optuna_w_mean_wape,
        optuna_w_global_bias=args.bin_optuna_w_global_bias,
    )

    target_transform = "log" if args.train_on_logy else args.target_transform

    gnn_config = GNNConfig(
        enabled=args.enable_gnn or ("gnn" in models_override if models_override else False) or ("gnn" in extra_models),
        dataset_dir=args.gnn_dataset_dir,
        inference_dataset_dir=args.gnn_inference_dataset_dir,
        part_key_col=args.gnn_part_key_col,
        device=args.gnn_device,
        hidden_dim=args.gnn_hidden_dim,
        num_layers=args.gnn_num_layers,
        dropout=args.gnn_dropout,
        train_eps=args.gnn_train_eps,
        epochs=args.gnn_epochs,
        batch_size=args.gnn_batch_size,
        eval_batch_size=args.gnn_eval_batch_size,
        lr=args.gnn_lr,
        weight_decay=args.gnn_weight_decay,
        loss=args.gnn_loss,
        monitor_metric=args.gnn_monitor_metric,
        lr_factor=args.gnn_lr_factor,
        lr_patience=args.gnn_lr_patience,
        early_stopping_patience=args.gnn_early_stopping_patience,
        min_delta=args.gnn_min_delta,
        prediction_cap_multiplier=args.gnn_prediction_cap_multiplier,
        grad_clip_norm=args.gnn_grad_clip_norm,
        weighted_loss_enabled=args.gnn_weighted_loss_enabled,
        weighted_loss_bins=args.gnn_weighted_loss_bins,
        weighted_loss_power=args.gnn_weighted_loss_power,
        weighted_loss_max_weight=args.gnn_weighted_loss_max_weight,
        weighted_sampler_enabled=args.gnn_weighted_sampler_enabled,
        weighted_sampler_power=args.gnn_weighted_sampler_power,
        weighted_sampler_max_weight=args.gnn_weighted_sampler_max_weight,
    )


    gnn_optuna_config = GNNOptunaConfig(
        enabled=args.gnn_optuna_enabled,
        epochs_override=args.gnn_optuna_epochs,
        early_stopping_patience_override=args.gnn_optuna_early_stopping_patience,
        eval_batch_size_override=args.gnn_optuna_eval_batch_size,
        min_delta_override=args.gnn_optuna_min_delta,
        hidden_dim_choices=[int(v) for v in _parse_csv_list(args.gnn_optuna_hidden_dims)],
        num_layers_choices=[int(v) for v in _parse_csv_list(args.gnn_optuna_num_layers)],
        dropout_range=(float(args.gnn_optuna_dropout_min), float(args.gnn_optuna_dropout_max)),
        lr_range=(float(args.gnn_optuna_lr_min), float(args.gnn_optuna_lr_max)),
        weight_decay_range=(float(args.gnn_optuna_weight_decay_min), float(args.gnn_optuna_weight_decay_max)),
        batch_size_choices=[int(v) for v in _parse_csv_list(args.gnn_optuna_batch_sizes)],
        loss_choices=_parse_csv_list(args.gnn_optuna_losses),
        train_eps_choices=_parse_bool_csv(args.gnn_optuna_train_eps),
        reject_on_nonfinite=args.gnn_optuna_reject_on_nonfinite,
        reject_score_value=args.gnn_optuna_reject_score_value,
        reject_pred_above_train_multiplier=args.gnn_optuna_reject_pred_above_train_multiplier,
        reject_train_cv_ratio=args.gnn_optuna_reject_train_cv_ratio,
    )

    business_loss_config = BusinessLossConfig(
        enabled=args.business_enabled,
        small_target_threshold=args.small_target_threshold,
        small_abs_error_limit=args.small_abs_error_limit,
        large_pct_error_to_true_limit=args.large_pct_error_to_true_limit,
        large_pct_error_to_pred_limit=args.large_pct_error_to_pred_limit,
        denom_eps=args.business_denom_eps,
        excess_power=args.business_excess_power,
        optuna_existing_score_weight=args.business_optuna_existing_score_weight,
        optuna_business_score_weight=args.business_optuna_score_weight,
        w_small_violation_rate=args.business_w_small_violation_rate,
        w_small_excess_mean=args.business_w_small_excess_mean,
        w_large_true_violation_rate=args.business_w_large_true_violation_rate,
        w_large_true_excess_mean=args.business_w_large_true_excess_mean,
        w_large_pred_violation_rate=args.business_w_large_pred_violation_rate,
        w_large_pred_excess_mean=args.business_w_large_pred_excess_mean,
    )

    config = EnsembleConfig(
        target_col=args.target_col,
        group_col=args.group_col,
        n_splits=args.n_splits,
        random_state=args.random_state,
        stratify_target_bins=args.stratify_target_bins,
        n_target_bins=args.n_target_bins,
        balance_columns=balance_columns,
        balance_min_count=args.balance_min_count,
        balance_fillna_value=args.balance_fillna_value,
        balance_rare_value=args.balance_rare_value,
        use_optuna=args.use_optuna,
        optuna_trials=args.optuna_trials,
        optuna_timeout=args.optuna_timeout,
        optuna_n_splits=args.optuna_n_splits,
        cv_score_mode=args.cv_score_mode,
        optuna_objective_mode=args.optuna_objective_mode,
        optuna_test_score_weight=args.optuna_test_score_weight,
        ensemble_mode=args.ensemble_mode,
        metric_name=args.metric_name,
        mape_smooth_alpha=args.mape_smooth_alpha,
        pct_error_sum_tail_weight=args.pct_error_sum_tail_weight,
        pct_error_sum_tail_quantile=args.pct_error_sum_tail_quantile,
        target_transform=target_transform,
        final_fit_mode=args.final_fit_mode,
        hybrid_full_weight=args.hybrid_full_weight,
        custom_params=_parse_json_dict(args.custom_params_json),
        bin_metric_config=bin_metric_config,
        business_loss_config=business_loss_config,
        gnn_config=gnn_config,
        gnn_optuna_config=gnn_optuna_config,
    )

    _validate_test_dataframe_columns(
        test_df,
        feature_spec=feature_spec,
        group_col=args.group_col,
        balance_columns=balance_columns,
        gnn_enabled=gnn_config.enabled,
        gnn_part_key_col=args.gnn_part_key_col,
        explicit_test_target_col=args.test_target_col,
        fallback_target_col=args.target_col,
        optuna_test_score_weight=args.optuna_test_score_weight,
        complexity_clf_enabled=args.complexity_clf_enabled,
    )

    trainer = FlexibleRegressorEnsemble(
        feature_spec=feature_spec,
        model_flags=model_flags,
        config=config,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    optuna_test_target_col = None
    if test_df is not None and args.optuna_test_score_weight > 0.0:
        optuna_test_target_col = _resolve_eval_target_col(test_df, args.test_target_col, args.target_col)
        if optuna_test_target_col is None:
            raise ValueError("optuna_test_score_weight > 0, но в test_df не найден target-col для оценки")

    oof_df = trainer.fit_predict_oof(
        train_df,
        optuna_test_df=test_df if args.optuna_test_score_weight > 0.0 else None,
        optuna_test_target_col=optuna_test_target_col,
        include_fold_columns=args.final_fit_mode in {"fold_ensemble", "hybrid"},
    )
    summary = trainer.get_summary()
    metrics_table = trainer.get_oof_metrics_table()
    ensemble_bin_report = trainer.get_bin_report()

    fold_distribution_table = trainer.get_fold_distribution_table()
    segment_metrics_table = trainer.get_segment_metrics_table(
        df_source=train_df,
        segment_columns=list(dict.fromkeys(([args.group_col] if args.group_col else []) + balance_columns)),
        min_size=5,
    )
    worst_cases_summary = trainer.get_worst_cases_summary(
        top_n=50,
        sort_by="business_rule_penalty",
    )
    feature_importances_table = _collect_feature_importances(
        trainer=trainer,
        model_names=fi_models,
        top_n=args.feature_importance_top_n,
        aggregate=args.feature_importance_aggregate,
        normalize=args.feature_importance_normalize,
    )
    optuna_trials_metrics_table = _collect_optuna_trials_metrics(trainer)

    balance_columns_bin_report = trainer.get_balance_columns_bin_report(
        df_source=train_df,
        balance_columns=balance_columns,
        pred_col="ensemble",
        min_segment_size=5,
    )

    suspicious_sheets: Dict[str, pd.DataFrame] = {}
    if args.suspicious_analysis:
        suspicious_seeds = build_repeated_oof_seeds(
            base_random_state=args.random_state,
            explicit_seeds=[int(x) for x in _parse_csv_list(args.suspicious_seeds)] if args.suspicious_seeds else None,
            n_seeds=5,
            step=101,
        )
        suspicious_model_groups = parse_model_groups_json(args.suspicious_model_groups_json)
        suspicious_sheets = run_repeated_oof_suspicious_analysis(
            df=train_df,
            feature_spec=feature_spec,
            base_config=config,
            seeds=suspicious_seeds,
            model_groups=suspicious_model_groups,
            material_col=args.suspicious_material_col,
            neighbors_k=args.suspicious_neighbors_k,
            id_col=args.suspicious_id_col,
            optuna_test_df=test_df if args.optuna_test_score_weight > 0.0 else None,
            optuna_test_target_col=optuna_test_target_col,
        )

    complexity_artifacts = None
    if args.complexity_clf_enabled:
        train_df_for_clf = train_df.loc[trainer.fit_filtered_df_index_].copy() if trainer.fit_filtered_df_index_ is not None else train_df.copy()
        complexity_artifacts = run_complexity_classifier_experiments(
            trainer=trainer,
            train_df=train_df_for_clf,
            threshold=float(args.complexity_clf_threshold),
            model_names=_parse_csv_list(args.complexity_clf_models),
            probability_threshold=float(args.complexity_clf_prob_threshold),
            probability_threshold_grid=_parse_float_list(args.complexity_clf_threshold_grid) if args.complexity_clf_threshold_grid else None,
            test_df=test_df,
            test_target_col=_resolve_eval_target_col(test_df, args.test_target_col, args.target_col) if test_df is not None else None,
        )

    sheets: Dict[str, pd.DataFrame] = {
        "oof_df": oof_df,
        "metrics_table": metrics_table,
        "ensemble_bin_report": ensemble_bin_report,
        "balance_columns_bin_report": balance_columns_bin_report,
        "summary": _summary_to_df(summary),
        "fold_distribution": fold_distribution_table,
        "segment_metrics": segment_metrics_table,
        "worst_cases_summary": worst_cases_summary,
        "feature_importances": feature_importances_table,
        "optuna_trials_metrics": optuna_trials_metrics_table,
        "autobrep_features": autobrep_features_table,
    }

    sheets.update(suspicious_sheets)
    if complexity_artifacts is not None:
        sheets.update(complexity_artifacts.to_sheets())

    if test_df is not None:
        test_pred_df = trainer.predict(
            test_df,
            include_detail_columns=args.final_fit_mode in {"fold_ensemble", "hybrid"},
        )
        # keep selected segment columns in predictions workbook for easier slicing
        for col in list(dict.fromkeys(([args.group_col] if args.group_col else []) + balance_columns)):
            if col in test_df.columns and col not in test_pred_df.columns:
                test_pred_df[col] = test_df[col].values

        sheets["test_predictions"] = test_pred_df

        eval_target_col = _resolve_eval_target_col(test_df, args.test_target_col, args.target_col)
        if eval_target_col is not None:
            y_test = test_df[eval_target_col].to_numpy(dtype=float)
            test_pred_eval_df, test_metrics_df, test_bin_report_df = _evaluate_predictions(
                trainer=trainer,
                pred_df=test_pred_df,
                y_true=y_test,
                target_col_name=eval_target_col,
            )
            sheets["test_predictions"] = test_pred_eval_df
            sheets["test_metrics"] = test_metrics_df
            sheets["test_bin_report"] = test_bin_report_df

            test_segment_metrics = _build_segment_metrics_from_pred_df(
                trainer=trainer,
                pred_df=test_pred_eval_df,
                segment_columns=list(dict.fromkeys(([args.group_col] if args.group_col else []) + balance_columns)),
                pred_col="ensemble",
                min_size=5,
            )
            sheets["test_segment_metrics"] = test_segment_metrics

    report_file = args.report_file or f"results_{args.suffix}.xlsx"
    workbook_path = out_dir / report_file
    _write_results_workbook(workbook_path, sheets)

    bundle_info = None
    if args.save_bundle_path:
        extra_artifacts: Dict[str, object] = {}
        if complexity_artifacts is not None:
            extra_artifacts["complexity_classifier"] = complexity_artifacts.to_bundle_payload()
        bundle_info = trainer.save_bundle(args.save_bundle_path, extra_artifacts=extra_artifacts)

    print("CV scores:", summary["cv_scores"])
    print("Weights:", summary["model_weights"])
    print("Balance columns:", summary.get("balance_columns"))
    print("CV score mode:", summary.get("cv_score_mode"))
    print("Optuna objective mode:", summary.get("optuna_objective_mode"))
    print("Optuna test score weight:", summary.get("optuna_test_score_weight"))
    print("Target transform:", summary.get("target_transform"))
    print("Final fit mode:", summary.get("final_fit_mode"))
    print("Hybrid full weight:", summary.get("hybrid_full_weight"))
    print("Split strata unique:", summary.get("split_strat_nunique"))
    if autobrep_embedding_cols or autobrep_numeric_cols:
        print("AutoBrep embedding cols:", autobrep_embedding_cols)
        print("AutoBrep numeric cols:", autobrep_numeric_cols)
    if complexity_artifacts is not None:
        print("Complexity classifier models:", complexity_artifacts.settings.get("model_names"))
        print("Complexity classifier threshold:", complexity_artifacts.settings.get("threshold"))
    print("Workbook:", workbook_path)
    if bundle_info is not None:
        print("Bundle:", bundle_info.get("bundle_path"))
        print("Bundle manifest:", bundle_info.get("manifest_path"))
