from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

from ml_models.flexible_ensemble.trainer import FlexibleRegressorEnsemble


DEFAULT_PROBABILITY_THRESHOLDS: List[float] = [
    0.05, 0.10, 0.15, 0.20, 0.25,
    0.30, 0.35, 0.40, 0.45, 0.50,
    0.55, 0.60, 0.65, 0.70, 0.75,
    0.80, 0.85, 0.90, 0.95,
]


class _ConstantProbabilityClassifier:
    def __init__(self, probability_positive: float) -> None:
        self.probability_positive = float(np.clip(probability_positive, 0.0, 1.0))

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "_ConstantProbabilityClassifier":
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p1 = np.full(len(X), self.probability_positive, dtype=float)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])


@dataclass
class ComplexityClassifierArtifacts:
    settings: Dict[str, Any] = field(default_factory=dict)
    full_models: Dict[str, Any] = field(default_factory=dict)
    oof_predictions: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    threshold_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    confusion_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    per_fold_metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    test_predictions: pd.DataFrame = field(default_factory=pd.DataFrame)
    test_metrics_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    test_threshold_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    test_confusion_table: pd.DataFrame = field(default_factory=pd.DataFrame)

    def to_sheets(self) -> Dict[str, pd.DataFrame]:
        sheets: Dict[str, pd.DataFrame] = {
            "complexity_clf_metrics": self.metrics_table,
            "complexity_clf_thresholds": self.threshold_table,
            "complexity_clf_confusion": self.confusion_table,
            "complexity_clf_oof": self.oof_predictions,
            "complexity_clf_per_fold": self.per_fold_metrics,
        }
        if self.test_predictions is not None and not self.test_predictions.empty:
            sheets["complexity_clf_test_predictions"] = self.test_predictions
        if self.test_metrics_table is not None and not self.test_metrics_table.empty:
            sheets["complexity_clf_test_metrics"] = self.test_metrics_table
        if self.test_threshold_table is not None and not self.test_threshold_table.empty:
            sheets["complexity_clf_test_thresholds"] = self.test_threshold_table
        if self.test_confusion_table is not None and not self.test_confusion_table.empty:
            sheets["complexity_clf_test_confusion"] = self.test_confusion_table
        return sheets

    def to_bundle_payload(self) -> Dict[str, Any]:
        return {
            "settings": dict(self.settings),
            "full_models": dict(self.full_models),
            "metrics_table": self.metrics_table.copy(),
            "threshold_table": self.threshold_table.copy(),
            "confusion_table": self.confusion_table.copy(),
            "per_fold_metrics": self.per_fold_metrics.copy(),
            "test_metrics_table": self.test_metrics_table.copy(),
            "test_threshold_table": self.test_threshold_table.copy(),
            "test_confusion_table": self.test_confusion_table.copy(),
        }


def _safe_average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if np.unique(y_true).size < 2:
        return float("nan")
    return float(average_precision_score(y_true, y_score))


def _safe_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if np.unique(y_true).size < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def _confusion_counts(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, int]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def _build_metrics_row(
    *,
    model_name: str,
    dataset_name: str,
    y_true: np.ndarray,
    y_score: np.ndarray,
    probability_threshold: float,
) -> Dict[str, Any]:
    y_pred = (np.asarray(y_score, dtype=float) >= float(probability_threshold)).astype(int)
    confusion = _confusion_counts(y_true, y_pred)
    return {
        "model": model_name,
        "dataset": dataset_name,
        "probability_threshold": float(probability_threshold),
        "n": int(len(y_true)),
        "positives_true": int(np.sum(y_true)),
        "positive_rate_true": float(np.mean(y_true)) if len(y_true) else float("nan"),
        "positives_pred": int(np.sum(y_pred)),
        "positive_rate_pred": float(np.mean(y_pred)) if len(y_pred) else float("nan"),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": _safe_average_precision(y_true, y_score),
        "roc_auc": _safe_roc_auc(y_true, y_score),
        **confusion,
    }


def _build_threshold_table(
    *,
    model_name: str,
    dataset_name: str,
    y_true: np.ndarray,
    y_score: np.ndarray,
    thresholds: Iterable[float],
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for thr in thresholds:
        rows.append(
            _build_metrics_row(
                model_name=model_name,
                dataset_name=dataset_name,
                y_true=y_true,
                y_score=y_score,
                probability_threshold=float(thr),
            )
        )
    return pd.DataFrame(rows)


def _extract_confusion_table(metrics_df: pd.DataFrame) -> pd.DataFrame:
    if metrics_df.empty:
        return pd.DataFrame()
    keep_cols = [
        "model",
        "dataset",
        "probability_threshold",
        "tn",
        "fp",
        "fn",
        "tp",
        "n",
        "positives_true",
        "positives_pred",
    ]
    return metrics_df[keep_cols].copy()


def _build_classifier(
    trainer: FlexibleRegressorEnsemble,
    model_name: str,
) -> Any:
    rs = int(trainer.config.random_state)
    if model_name == "logreg":
        pre = trainer._make_sklearn_preprocessor(scale_numeric=True)
        model = LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            solver="liblinear",
            random_state=rs,
        )
        return Pipeline([("preprocessor", pre), ("model", model)])

    if model_name == "lgbm":
        try:
            from lightgbm import LGBMClassifier
        except ImportError as e:
            raise ImportError("lightgbm не установлен, а complexity classifier lgbm запрошен") from e
        return LGBMClassifier(
            n_estimators=500,
            learning_rate=0.03,
            num_leaves=31,
            max_depth=-1,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=rs,
            n_jobs=-1,
            verbosity=-1,
            class_weight="balanced",
        )

    if model_name == "catboost":
        try:
            from catboost import CatBoostClassifier
        except ImportError as e:
            raise ImportError("catboost не установлен, а complexity classifier catboost запрошен") from e
        return CatBoostClassifier(
            iterations=700,
            learning_rate=0.03,
            depth=6,
            loss_function="Logloss",
            eval_metric="PRAUC",
            random_seed=rs,
            auto_class_weights="Balanced",
            verbose=False,
        )

    raise ValueError(f"Неизвестная модель complexity classifier: {model_name}")


def _fit_classifier(
    trainer: FlexibleRegressorEnsemble,
    model_name: str,
    X: pd.DataFrame,
    y: np.ndarray,
) -> Any:
    if np.unique(y).size < 2:
        return _ConstantProbabilityClassifier(probability_positive=float(np.mean(y)))

    model = _build_classifier(trainer, model_name)
    if model_name == "logreg":
        model.fit(X[trainer.base_feature_columns_], y)
        return model

    if model_name == "lgbm":
        X_fit, cat_features = trainer._prepare_lgbm_input(X)
        fit_kwargs = {"X": X_fit, "y": y, "feature_name": list(X_fit.columns)}
        if cat_features:
            fit_kwargs["categorical_feature"] = cat_features
        model.fit(**fit_kwargs)
        return model

    if model_name == "catboost":
        X_fit = trainer._prepare_catboost_input(X)
        fit_kwargs = {"X": X_fit, "y": y, "verbose": False}
        if trainer.feature_spec.categorical_features:
            fit_kwargs["cat_features"] = trainer.feature_spec.categorical_features
        if trainer.catboost_native_embedding_columns_:
            fit_kwargs["embedding_features"] = trainer.catboost_native_embedding_columns_
        model.fit(**fit_kwargs)
        return model

    raise ValueError(f"Неизвестная модель complexity classifier: {model_name}")


def _predict_classifier_proba(
    trainer: FlexibleRegressorEnsemble,
    model_name: str,
    model: Any,
    X: pd.DataFrame,
) -> np.ndarray:
    if model_name == "logreg":
        proba = np.asarray(model.predict_proba(X[trainer.base_feature_columns_]), dtype=float)
        return proba[:, 1]

    if model_name == "lgbm":
        X_pred, _ = trainer._prepare_lgbm_input(X)
        proba = np.asarray(model.predict_proba(X_pred), dtype=float)
        return proba[:, 1]

    if model_name == "catboost":
        X_pred = trainer._prepare_catboost_input(X)
        proba = np.asarray(model.predict_proba(X_pred), dtype=float)
        return proba[:, 1]

    raise ValueError(f"Неизвестная модель complexity classifier: {model_name}")


def run_complexity_classifier_experiments(
    *,
    trainer: FlexibleRegressorEnsemble,
    train_df: pd.DataFrame,
    threshold: float,
    model_names: List[str],
    probability_threshold: float = 0.5,
    probability_threshold_grid: Optional[List[float]] = None,
    test_df: Optional[pd.DataFrame] = None,
    test_target_col: Optional[str] = None,
) -> ComplexityClassifierArtifacts:
    trainer._check_is_fitted()
    if trainer.fold_assignments_ is None or trainer.fold_assignments_.empty:
        raise RuntimeError("Для complexity classifier нужны сохранённые fold assignments после fit().")

    model_names = list(dict.fromkeys([str(m).strip().lower() for m in (model_names or []) if str(m).strip()]))
    if not model_names:
        raise ValueError("Не задано ни одной модели для complexity classifier")

    thresholds = probability_threshold_grid or list(DEFAULT_PROBABILITY_THRESHOLDS)
    thresholds = sorted({float(np.clip(t, 0.0, 1.0)) for t in thresholds})
    if float(probability_threshold) not in thresholds:
        thresholds = sorted(set(thresholds + [float(probability_threshold)]))

    X_train = trainer._build_feature_frame(train_df, fit_mode=False)
    y_train_raw = train_df[trainer.config.target_col].to_numpy(dtype=float)
    y_train_bin = (y_train_raw >= float(threshold)).astype(int)

    fold_assign = trainer.fold_assignments_.reindex(train_df.index)
    if fold_assign["fold_id"].isna().any():
        raise ValueError("Не удалось сопоставить fold assignments с train_df для complexity classifier")
    fold_ids = fold_assign["fold_id"].to_numpy(dtype=int)

    metrics_rows: List[Dict[str, Any]] = []
    per_fold_rows: List[Dict[str, Any]] = []
    threshold_tables: List[pd.DataFrame] = []
    oof_df = pd.DataFrame(index=train_df.index)
    oof_df[trainer.config.target_col] = y_train_raw
    oof_df["complexity_target"] = y_train_bin

    full_models: Dict[str, Any] = {}
    test_predictions = pd.DataFrame(index=test_df.index) if test_df is not None else pd.DataFrame()
    test_metrics_rows: List[Dict[str, Any]] = []
    test_threshold_tables: List[pd.DataFrame] = []

    X_test = trainer._build_feature_frame(test_df, fit_mode=False) if test_df is not None else None
    y_test_bin: Optional[np.ndarray] = None
    if test_df is not None and test_target_col and test_target_col in test_df.columns:
        y_test_bin = (test_df[test_target_col].to_numpy(dtype=float) >= float(threshold)).astype(int)
        test_predictions[test_target_col] = test_df[test_target_col].to_numpy(dtype=float)
        test_predictions["complexity_target"] = y_test_bin

    unique_fold_ids = [int(v) for v in sorted(pd.unique(fold_ids)) if int(v) >= 0]

    for model_name in model_names:
        oof_proba = np.full(len(train_df), np.nan, dtype=float)

        for fold_id in unique_fold_ids:
            va_mask = fold_ids == fold_id
            tr_mask = ~va_mask
            X_tr = X_train.iloc[np.where(tr_mask)[0]].copy()
            X_va = X_train.iloc[np.where(va_mask)[0]].copy()
            y_tr = y_train_bin[tr_mask]
            y_va = y_train_bin[va_mask]

            model = _fit_classifier(trainer, model_name, X_tr, y_tr)
            fold_proba = _predict_classifier_proba(trainer, model_name, model, X_va)
            oof_proba[va_mask] = fold_proba

            fold_row = _build_metrics_row(
                model_name=model_name,
                dataset_name="train_oof_fold",
                y_true=y_va,
                y_score=fold_proba,
                probability_threshold=float(probability_threshold),
            )
            fold_row["fold_id"] = int(fold_id)
            per_fold_rows.append(fold_row)

        if np.isnan(oof_proba).any():
            raise RuntimeError(f"OOF probability содержит NaN для модели {model_name}")

        oof_df[f"{model_name}__proba"] = oof_proba
        oof_df[f"{model_name}__pred"] = (oof_proba >= float(probability_threshold)).astype(int)

        metrics_rows.append(
            _build_metrics_row(
                model_name=model_name,
                dataset_name="train_oof",
                y_true=y_train_bin,
                y_score=oof_proba,
                probability_threshold=float(probability_threshold),
            )
        )
        threshold_tables.append(
            _build_threshold_table(
                model_name=model_name,
                dataset_name="train_oof",
                y_true=y_train_bin,
                y_score=oof_proba,
                thresholds=thresholds,
            )
        )

        full_model = _fit_classifier(trainer, model_name, X_train, y_train_bin)
        full_models[model_name] = full_model

        if X_test is not None:
            test_proba = _predict_classifier_proba(trainer, model_name, full_model, X_test)
            test_predictions[f"{model_name}__proba"] = test_proba
            test_predictions[f"{model_name}__pred"] = (test_proba >= float(probability_threshold)).astype(int)
            if y_test_bin is not None:
                test_metrics_rows.append(
                    _build_metrics_row(
                        model_name=model_name,
                        dataset_name="test",
                        y_true=y_test_bin,
                        y_score=test_proba,
                        probability_threshold=float(probability_threshold),
                    )
                )
                test_threshold_tables.append(
                    _build_threshold_table(
                        model_name=model_name,
                        dataset_name="test",
                        y_true=y_test_bin,
                        y_score=test_proba,
                        thresholds=thresholds,
                    )
                )

    metrics_table = pd.DataFrame(metrics_rows)
    threshold_table = pd.concat(threshold_tables, axis=0, ignore_index=True) if threshold_tables else pd.DataFrame()
    confusion_table = _extract_confusion_table(metrics_table)
    per_fold_metrics = pd.DataFrame(per_fold_rows)

    test_metrics_table = pd.DataFrame(test_metrics_rows)
    test_threshold_table = pd.concat(test_threshold_tables, axis=0, ignore_index=True) if test_threshold_tables else pd.DataFrame()
    test_confusion_table = _extract_confusion_table(test_metrics_table)

    return ComplexityClassifierArtifacts(
        settings={
            "threshold": float(threshold),
            "probability_threshold": float(probability_threshold),
            "probability_threshold_grid": list(thresholds),
            "model_names": list(model_names),
            "target_col": trainer.config.target_col,
        },
        full_models=full_models,
        oof_predictions=oof_df,
        metrics_table=metrics_table,
        threshold_table=threshold_table,
        confusion_table=confusion_table,
        per_fold_metrics=per_fold_metrics,
        test_predictions=test_predictions,
        test_metrics_table=test_metrics_table,
        test_threshold_table=test_threshold_table,
        test_confusion_table=test_confusion_table,
    )
