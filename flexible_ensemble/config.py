from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal, Tuple


@dataclass
class FeatureSpec:
    numeric_features: List[str]
    categorical_features: Optional[List[str]] = field(default_factory=list)
    embedding_features: Optional[List[str]] = field(default_factory=list)
    catboost_embedding_features: Optional[List[str]] = field(default_factory=list)

    def __post_init__(self):
        self.numeric_features = list(self.numeric_features or [])
        self.categorical_features = list(self.categorical_features or [])
        self.embedding_features = list(self.embedding_features or [])
        self.catboost_embedding_features = list(self.catboost_embedding_features or [])


@dataclass
class ModelFlags:
    use_mlp: bool = True
    use_lgbm: bool = True
    use_catboost: bool = True
    use_xgb: bool = True
    use_rf: bool = True
    use_gnn: bool = False

    extra_models: Optional[List[str]] = field(default_factory=list)
    models_override: Optional[List[str]] = None

    def __post_init__(self) -> None:
        self.extra_models = list(self.extra_models or [])
        if self.models_override is not None:
            self.models_override = list(self.models_override or [])

    def gnn_requested(self) -> bool:
        override = set(self.models_override or [])
        extra = set(self.extra_models or [])
        return bool(self.use_gnn or "gnn" in override or "gnn" in extra)


@dataclass
class GNNConfig:
    enabled: bool = False
    dataset_dir: Optional[str] = None
    inference_dataset_dir: Optional[str] = None
    part_key_col: Optional[str] = None
    device: Optional[str] = None

    hidden_dim: int = 96
    num_layers: int = 4
    dropout: float = 0.15
    train_eps: bool = False

    epochs: int = 300
    batch_size: int = 24
    eval_batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    loss: Literal["huber", "mse", "l1"] = "huber"
    monitor_metric: Literal["rmse", "mae", "rmsle", "mape_pct", "wape_pct"] = "rmsle"
    lr_factor: float = 0.5
    lr_patience: int = 12
    early_stopping_patience: int = 30
    min_delta: float = 1e-5

    prediction_cap_multiplier: float = 2.0
    grad_clip_norm: float = 1.0

    weighted_loss_enabled: bool = True
    weighted_loss_bins: int = 5
    weighted_loss_power: float = 0.5
    weighted_loss_max_weight: float = 5.0

    weighted_sampler_enabled: bool = True
    weighted_sampler_power: float = 0.5
    weighted_sampler_max_weight: float = 5.0




@dataclass
class GNNOptunaConfig:
    enabled: bool = True

    epochs_override: Optional[int] = 120
    early_stopping_patience_override: Optional[int] = 20
    eval_batch_size_override: Optional[int] = None
    min_delta_override: Optional[float] = None

    hidden_dim_choices: List[int] = field(default_factory=lambda: [64, 96, 128])
    num_layers_choices: List[int] = field(default_factory=lambda: [3, 4])
    dropout_range: Tuple[float, float] = (0.10, 0.30)
    lr_range: Tuple[float, float] = (3e-4, 1e-3)
    weight_decay_range: Tuple[float, float] = (1e-5, 1e-3)
    batch_size_choices: List[int] = field(default_factory=lambda: [16, 24, 32])
    loss_choices: List[str] = field(default_factory=lambda: ["huber", "l1"])
    train_eps_choices: List[bool] = field(default_factory=lambda: [False])

    reject_on_nonfinite: bool = True
    reject_score_value: float = 1e9
    reject_pred_above_train_multiplier: float = 3.0
    reject_train_cv_ratio: float = 20.0

    def __post_init__(self) -> None:
        self.hidden_dim_choices = [int(v) for v in (self.hidden_dim_choices or [64, 96, 128, 160])]
        self.num_layers_choices = [int(v) for v in (self.num_layers_choices or [3, 4, 5, 6])]
        self.batch_size_choices = [int(v) for v in (self.batch_size_choices or [16, 24, 32, 48])]
        self.loss_choices = [str(v) for v in (self.loss_choices or ["huber", "mse", "l1"])]
        self.train_eps_choices = [bool(v) for v in (self.train_eps_choices or [False, True])]
        if len(self.dropout_range) != 2 or float(self.dropout_range[0]) > float(self.dropout_range[1]):
            raise ValueError("GNNOptunaConfig.dropout_range должен быть парой (min, max)")
        if len(self.lr_range) != 2 or float(self.lr_range[0]) > float(self.lr_range[1]):
            raise ValueError("GNNOptunaConfig.lr_range должен быть парой (min, max)")
        if len(self.weight_decay_range) != 2 or float(self.weight_decay_range[0]) > float(self.weight_decay_range[1]):
            raise ValueError("GNNOptunaConfig.weight_decay_range должен быть парой (min, max)")


@dataclass
class BinMetricConfig:
    enabled: bool = True
    strategy: Literal["fixed", "quantile"] = "fixed"
    fixed_edges: Optional[List[float]] = field(default_factory=lambda: [0.5, 1.0, 2.0, 5.0, 10.0])
    n_bins: int = 6
    min_bin_size: int = 5
    ape_floor: float = 0.25
    bin_weights: Optional[Dict[int, float]] = field(default_factory=dict)
    optuna_w_mean_bin_rmsle: float = 0.55
    optuna_w_std_bin_rmsle: float = 0.15
    optuna_w_mean_bin_wape: float = 0.20
    optuna_w_global_bias: float = 0.10


@dataclass
class BusinessLossConfig:
    enabled: bool = True
    small_target_threshold: float = 1.0
    small_abs_error_limit: float = 1.0
    large_pct_error_to_true_limit: float = 1.0
    large_pct_error_to_pred_limit: float = 1.0
    denom_eps: float = 1e-6
    excess_power: float = 2.0
    optuna_existing_score_weight: float = 0.65
    optuna_business_score_weight: float = 0.35
    w_small_violation_rate: float = 0.30
    w_small_excess_mean: float = 0.30
    w_large_true_violation_rate: float = 0.15
    w_large_true_excess_mean: float = 0.10
    w_large_pred_violation_rate: float = 0.10
    w_large_pred_excess_mean: float = 0.05


@dataclass
class EnsembleConfig:
    target_col: str
    group_col: Optional[str] = None

    n_splits: int = 5
    random_state: int = 42
    stratify_target_bins: bool = True
    n_target_bins: int = 5

    balance_columns: Optional[List[str]] = field(default_factory=list)
    balance_min_count: Optional[int] = None
    balance_fillna_value: str = "__MISSING__"
    balance_rare_value: str = "__RARE__"

    use_optuna: bool = True
    optuna_trials: int = 25
    optuna_timeout: Optional[int] = None
    optuna_n_splits: int = 3
    cv_score_mode: Literal["composite_optuna", "standard"] = "composite_optuna"
    optuna_objective_mode: Literal[
        "composite_optuna",
        "pct_error_sum",
        "pct_error_sum_tail",
        "pct_error_sum_bin_balanced",
        "metric_name"
    ] = "composite_optuna"
    optuna_test_score_weight: float = 0.0

    ensemble_mode: str = "weighted"
    metric_name: str = "rmsle"

    mape_smooth_alpha: float = 1.0
    pct_error_sum_tail_weight: float = 0.30
    pct_error_sum_tail_quantile: float = 0.90

    target_transform: Literal["none", "log", "log1p"] = "none"
    final_fit_mode: Literal["full_refit", "fold_ensemble", "hybrid"] = "full_refit"
    hybrid_full_weight: float = 0.5

    custom_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    bin_metric_config: BinMetricConfig = field(default_factory=BinMetricConfig)
    business_loss_config: BusinessLossConfig = field(default_factory=BusinessLossConfig)
    gnn_config: GNNConfig = field(default_factory=GNNConfig)
    gnn_optuna_config: GNNOptunaConfig = field(default_factory=GNNOptunaConfig)

    def __post_init__(self) -> None:
        self.balance_columns = list(self.balance_columns or [])
