from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold, StratifiedGroupKFold, StratifiedKFold


class SplittingMixin:
    def _make_target_bins(self, y: np.ndarray) -> np.ndarray:
            if not self.config.stratify_target_bins:
                return np.zeros(len(y), dtype=int)

            n_unique = len(np.unique(y))
            n_bins = max(2, min(self.config.n_target_bins, n_unique))
            ranked = pd.Series(y).rank(method="first")
            bins = pd.qcut(ranked, q=n_bins, labels=False, duplicates="drop")
            return bins.astype(int).to_numpy()

    def _normalize_balance_series(self, s: pd.Series) -> pd.Series:
            return s.astype("string").fillna(self.config.balance_fillna_value).astype(str)

    def _build_split_strat_labels(
            self,
            df: pd.DataFrame,
            y: np.ndarray,
            n_splits: int,
        ) -> Optional[np.ndarray]:
            """
            Строим страты для splitter:
            - только по target bins
            - или по (target_bin × balance_columns)
            - или только по balance_columns, если stratify_target_bins=False

            Если составная страта слишком редкая, откатываемся к более грубой.
            """
            use_target_bins = self.config.stratify_target_bins and len(np.unique(y)) > 1
            y_bins = self._make_target_bins(y) if use_target_bins else np.zeros(len(y), dtype=int)

            balance_columns = list(self.config.balance_columns or [])
            if not use_target_bins and not balance_columns:
                return None

            strata_df = pd.DataFrame(index=df.index)
            strata_df["y_bin"] = y_bins.astype(str)

            for col in balance_columns:
                strata_df[col] = self._normalize_balance_series(df[col])

            if use_target_bins and balance_columns:
                full_labels = strata_df.astype(str).agg("||".join, axis=1)
                fallback_labels = strata_df["y_bin"].astype(str)
            elif use_target_bins:
                full_labels = strata_df["y_bin"].astype(str)
                fallback_labels = full_labels
            else:
                full_labels = strata_df[balance_columns].astype(str).agg("||".join, axis=1)
                fallback_labels = pd.Series(
                    self.config.balance_rare_value,
                    index=df.index,
                    dtype="string",
                )

            min_count = self.config.balance_min_count or n_splits
            counts = full_labels.value_counts(dropna=False)
            labels = full_labels.where(full_labels.map(counts) >= min_count, fallback_labels)

            if not use_target_bins:
                counts2 = labels.value_counts(dropna=False)
                labels = labels.where(
                    labels.map(counts2) >= min_count,
                    self.config.balance_rare_value,
                )

            if labels.nunique(dropna=False) <= 1:
                if use_target_bins:
                    return strata_df["y_bin"].astype(str).to_numpy()
                return None

            return labels.astype(str).to_numpy()

    def _iter_splits(
            self,
            X: pd.DataFrame,
            y: np.ndarray,
            groups: Optional[np.ndarray],
            n_splits: int,
            strat_labels: Optional[np.ndarray] = None,
        ):
            use_strat = strat_labels is not None and len(pd.unique(pd.Series(strat_labels))) > 1

            if groups is not None and use_strat:
                splitter = StratifiedGroupKFold(
                    n_splits=n_splits,
                    shuffle=True,
                    random_state=self.config.random_state,
                )
                yield from splitter.split(X, strat_labels, groups)

            elif groups is not None:
                splitter = GroupKFold(n_splits=n_splits)
                yield from splitter.split(X, y, groups)

            elif use_strat:
                splitter = StratifiedKFold(
                    n_splits=n_splits,
                    shuffle=True,
                    random_state=self.config.random_state,
                )
                yield from splitter.split(X, strat_labels)

            else:
                splitter = KFold(
                    n_splits=n_splits,
                    shuffle=True,
                    random_state=self.config.random_state,
                )
                yield from splitter.split(X, y)

