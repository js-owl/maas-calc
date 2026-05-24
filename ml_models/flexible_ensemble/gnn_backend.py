from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import copy
import json
import os
import random

import numpy as np


KNOWN_EXTENSIONS = {".stp", ".step", ".brep", ".json", ".pt", ".pkl", ".pickle"}


def normalize_part_key(x: Any) -> str:
    s = str(x).strip().lower()
    if not s:
        return s
    suffix = Path(s).suffix.lower()
    if suffix in KNOWN_EXTENSIONS:
        s = Path(s).stem.lower().strip()
    return s


def _require_torch_modules():
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch.optim.lr_scheduler import ReduceLROnPlateau
        from torch_geometric.loader import DataLoader
        from torch_geometric.nn import (
            GINEConv,
            GraphNorm,
            global_add_pool,
            global_max_pool,
            global_mean_pool,
        )
    except ImportError as exc:
        raise ImportError(
            "Для модели GNN требуются torch и torch_geometric. Установите их перед использованием use_gnn=True."
        ) from exc
    return torch, nn, F, ReduceLROnPlateau, DataLoader, GINEConv, GraphNorm, global_add_pool, global_max_pool, global_mean_pool


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        torch, *_ = _require_torch_modules()
    except Exception:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_torch(path: Path):
    torch, *_ = _require_torch_modules()
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


@dataclass
class NormStats:
    node_mean: Any
    node_std: Any
    edge_mean: Any
    edge_std: Any
    node_start: int
    edge_start: int


@dataclass
class GNNModelBundle:
    model: Any
    norm_stats: NormStats
    model_kwargs: Dict[str, Any]
    device: Any
    fit_seed: int
    raw_prediction_upper: Optional[float] = None
    final_prediction_upper: Optional[float] = None


class GraphStore:
    def __init__(
        self,
        train_dataset_dir: str,
        inference_dataset_dir: Optional[str] = None,
    ) -> None:
        self.train_dataset_dir = Path(train_dataset_dir)
        self.inference_dataset_dir = Path(inference_dataset_dir) if inference_dataset_dir else None

        self.train_graphs_by_key, self.feature_spec = self._load_graph_dir(self.train_dataset_dir, require_spec=True)
        self.inference_graphs_by_key: Dict[str, Any] = {}
        if self.inference_dataset_dir is not None:
            self.inference_graphs_by_key, inf_spec = self._load_graph_dir(self.inference_dataset_dir, require_spec=False)
            if inf_spec is not None:
                self._assert_compatible_feature_specs(self.feature_spec, inf_spec, context=str(self.inference_dataset_dir))

        self.node_onehot_dim = len(self.feature_spec.get("surface_vocab", []))
        self.edge_onehot_dim = len(self.feature_spec.get("relation_vocab", []))

    @staticmethod
    def _assert_compatible_feature_specs(train_spec: Dict[str, Any], other_spec: Dict[str, Any], context: str) -> None:
        for key in ["surface_vocab", "relation_vocab", "node_numeric_features", "edge_numeric_features"]:
            if train_spec.get(key) != other_spec.get(key):
                raise ValueError(f"Feature spec mismatch for {context}: field '{key}' differs")

    @staticmethod
    def _load_feature_spec(dataset_dir: Path, required: bool = True) -> Optional[Dict[str, Any]]:
        spec_path = dataset_dir / "feature_spec.json"
        if not spec_path.exists():
            if required:
                raise FileNotFoundError(f"feature_spec.json not found in {dataset_dir}")
            return None
        return json.loads(spec_path.read_text(encoding="utf-8"))

    def _load_graph_dir(self, dataset_dir: Path, require_spec: bool) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        if not dataset_dir.exists():
            raise FileNotFoundError(f"GNN dataset dir not found: {dataset_dir}")
        graphs_path = dataset_dir / "graphs.pt"
        if not graphs_path.exists():
            raise FileNotFoundError(f"graphs.pt not found in {dataset_dir}")
        graphs = load_torch(graphs_path)
        if not isinstance(graphs, list) or len(graphs) == 0:
            raise ValueError(f"graphs.pt in {dataset_dir} must contain a non-empty list of PyG Data objects")
        by_key: Dict[str, Any] = {}
        for i, g in enumerate(graphs):
            key = normalize_part_key(getattr(g, "part_key", f"sample_{i:06d}"))
            if key in by_key:
                raise ValueError(f"Duplicate part_key in {dataset_dir}: {key}")
            by_key[key] = g
        spec = self._load_feature_spec(dataset_dir, required=require_spec)
        return by_key, spec

    def has_inference_graphs(self) -> bool:
        return bool(self.inference_graphs_by_key)

    def get_missing_part_keys(
        self,
        part_keys: Sequence[str],
        prefer_inference: bool = False,
    ) -> List[str]:
        missing: List[str] = []
        for raw_key in part_keys:
            key = normalize_part_key(raw_key)
            has_graph = False
            if prefer_inference and key in self.inference_graphs_by_key:
                has_graph = True
            elif key in self.train_graphs_by_key:
                has_graph = True
            elif key in self.inference_graphs_by_key:
                has_graph = True
            if not has_graph:
                missing.append(key)
        return missing

    def get_graphs_for_part_keys(
        self,
        part_keys: Sequence[str],
        prefer_inference: bool = False,
    ) -> List[Any]:
        out: List[Any] = []
        missing: List[str] = []
        for raw_key in part_keys:
            key = normalize_part_key(raw_key)
            g = None
            if prefer_inference and key in self.inference_graphs_by_key:
                g = self.inference_graphs_by_key[key]
            elif key in self.train_graphs_by_key:
                g = self.train_graphs_by_key[key]
            elif key in self.inference_graphs_by_key:
                g = self.inference_graphs_by_key[key]
            if g is None:
                missing.append(key)
            else:
                out.append(g)
        if missing:
            raise KeyError(
                f"Не найдены графы для {len(missing)} деталей. Примеры: {missing[:10]}"
            )
        return out


def fit_norm_stats(
    graphs: Sequence[Any],
    node_onehot_dim: int,
    edge_onehot_dim: int,
) -> NormStats:
    torch, *_ = _require_torch_modules()
    node_blocks: List[Any] = []
    edge_blocks: List[Any] = []
    for g in graphs:
        if g.x.size(1) > node_onehot_dim:
            node_blocks.append(g.x[:, node_onehot_dim:].float())
        if g.edge_attr.size(1) > edge_onehot_dim:
            edge_blocks.append(g.edge_attr[:, edge_onehot_dim:].float())

    if not node_blocks:
        raise ValueError("No node numeric features found for normalization")
    if not edge_blocks:
        raise ValueError("No edge numeric features found for normalization")

    node_cat = torch.cat(node_blocks, dim=0)
    edge_cat = torch.cat(edge_blocks, dim=0)
    node_mean = node_cat.mean(dim=0)
    node_std = node_cat.std(dim=0, unbiased=False).clamp_min(1e-8)
    edge_mean = edge_cat.mean(dim=0)
    edge_std = edge_cat.std(dim=0, unbiased=False).clamp_min(1e-8)
    return NormStats(
        node_mean=node_mean,
        node_std=node_std,
        edge_mean=edge_mean,
        edge_std=edge_std,
        node_start=node_onehot_dim,
        edge_start=edge_onehot_dim,
    )


def clone_and_normalize_graphs(graphs: Sequence[Any], stats: NormStats) -> List[Any]:
    out: List[Any] = []
    for g in graphs:
        h = g.clone()
        if h.x.size(1) > stats.node_start:
            h.x[:, stats.node_start:] = (h.x[:, stats.node_start:] - stats.node_mean) / stats.node_std
        if h.edge_attr.size(1) > stats.edge_start:
            h.edge_attr[:, stats.edge_start:] = (h.edge_attr[:, stats.edge_start:] - stats.edge_mean) / stats.edge_std
        out.append(h)
    return out


def attach_targets_to_graphs(graphs: Sequence[Any], y_values: Sequence[float]) -> List[Any]:
    torch, *_ = _require_torch_modules()
    out: List[Any] = []
    y_arr = np.asarray(y_values, dtype=np.float32)
    if len(graphs) != y_arr.shape[0]:
        raise ValueError("attach_targets_to_graphs: graphs and y_values have different lengths")
    for g, y in zip(graphs, y_arr):
        h = g.clone()
        h.y = torch.tensor([float(y)], dtype=torch.float32)
        out.append(h)
    return out


def attach_sample_weights_to_graphs(graphs: Sequence[Any], sample_weights: Sequence[float]) -> List[Any]:
    torch, *_ = _require_torch_modules()
    out: List[Any] = []
    w_arr = np.asarray(sample_weights, dtype=np.float32)
    if len(graphs) != w_arr.shape[0]:
        raise ValueError("attach_sample_weights_to_graphs: graphs and sample_weights have different lengths")
    for g, w in zip(graphs, w_arr):
        h = g.clone()
        h.sample_weight = torch.tensor([float(w)], dtype=torch.float32)
        out.append(h)
    return out


def extract_graph_targets(graphs: Sequence[Any]) -> np.ndarray:
    vals: List[float] = []
    for i, g in enumerate(graphs):
        if not hasattr(g, "y"):
            raise ValueError(f"Graph at index {i} has no target y")
        raw = getattr(g, "y")
        if hasattr(raw, "detach"):
            arr = raw.detach().cpu().numpy().astype(float).reshape(-1)
        else:
            arr = np.asarray(raw, dtype=float).reshape(-1)
        if arr.size == 0:
            raise ValueError(f"Graph at index {i} has empty target y")
        vals.append(float(arr[0]))
    return np.asarray(vals, dtype=np.float64)


def make_frequency_weights(
    y: Sequence[float],
    n_bins: int,
    power: float,
    max_weight: float,
) -> np.ndarray:
    y_arr = np.asarray(y, dtype=np.float64)
    if y_arr.size == 0:
        return np.empty((0,), dtype=np.float64)
    if int(n_bins) <= 1:
        return np.ones_like(y_arr, dtype=np.float64)
    quantiles = np.linspace(0.0, 1.0, int(n_bins) + 1)
    edges = np.quantile(y_arr, quantiles)
    edges = np.unique(edges)
    if edges.size <= 2:
        return np.ones_like(y_arr, dtype=np.float64)
    bin_ids = np.digitize(y_arr, edges[1:-1], right=False)
    counts = np.bincount(bin_ids, minlength=max(int(edges.size - 1), int(bin_ids.max()) + 1)).astype(np.float64)
    counts[counts <= 0.0] = 1.0
    weights = (float(y_arr.size) / counts[bin_ids]) ** float(power)
    weights = np.asarray(weights, dtype=np.float64)
    mean_w = float(np.mean(weights)) if weights.size else 1.0
    if mean_w > 0:
        weights = weights / mean_w
    if max_weight is not None and np.isfinite(max_weight) and max_weight > 0:
        weights = np.clip(weights, 1e-8, float(max_weight))
    return weights.astype(np.float64)


def build_gine_regressor(
    node_dim: int,
    edge_dim: int,
    hidden_dim: int = 96,
    num_layers: int = 4,
    dropout: float = 0.15,
    train_eps: bool = False,
):
    torch, nn, F, _, _, GINEConv, GraphNorm, global_add_pool, global_max_pool, global_mean_pool = _require_torch_modules()

    def make_mlp(in_dim: int, hidden_dim: int, out_dim: int, dropout: float):
        return nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim),
        )

    class GINEGraphRegressor(nn.Module):
        def __init__(self):
            super().__init__()
            self.node_proj = nn.Linear(node_dim, hidden_dim)
            self.convs = nn.ModuleList()
            self.norms = nn.ModuleList()
            self.dropout = float(dropout)

            for _ in range(num_layers):
                mlp = make_mlp(hidden_dim, hidden_dim, hidden_dim, dropout=dropout)
                self.convs.append(GINEConv(nn=mlp, train_eps=train_eps, edge_dim=edge_dim))
                self.norms.append(GraphNorm(hidden_dim))

            pooled_dim = hidden_dim * 3
            self.head = nn.Sequential(
                nn.Linear(pooled_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim // 2, 1),
            )

        def forward(self, batch):
            x = self.node_proj(batch.x)
            for conv, norm in zip(self.convs, self.norms):
                h = conv(x, batch.edge_index, batch.edge_attr)
                h = norm(h, batch.batch)
                h = F.relu(h)
                h = F.dropout(h, p=self.dropout, training=self.training)
                x = x + h
            g = torch.cat(
                [
                    global_add_pool(x, batch.batch),
                    global_mean_pool(x, batch.batch),
                    global_max_pool(x, batch.batch),
                ],
                dim=1,
            )
            return self.head(g).view(-1)

    return GINEGraphRegressor()


def get_device(device_str: Optional[str]):
    torch, *_ = _require_torch_modules()
    if device_str:
        return torch.device(device_str)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def transform_target_values(y: Any, target_transform: str):
    torch, *_ = _require_torch_modules()
    y = y.view(-1).float()
    if target_transform == "none":
        return y
    if target_transform == "log":
        if torch.any(y <= 0):
            raise ValueError("target_transform='log' требует строго положительные target для GNN")
        return torch.log(y)
    if target_transform == "log1p":
        if torch.any(y < -1):
            raise ValueError("target_transform='log1p' требует y >= -1 для GNN")
        return torch.log1p(y)
    raise ValueError(f"Неизвестный target_transform: {target_transform}")


def inverse_target_values(pred: np.ndarray, target_transform: str) -> np.ndarray:
    pred = np.asarray(pred, dtype=float)
    if target_transform == "none":
        return pred
    if target_transform == "log":
        return np.exp(pred)
    if target_transform == "log1p":
        return np.expm1(pred)
    raise ValueError(f"Неизвестный target_transform: {target_transform}")


def transform_prediction_upper(final_prediction_upper: Optional[float], target_transform: str) -> Optional[float]:
    if final_prediction_upper is None or not np.isfinite(final_prediction_upper):
        return None
    upper = float(final_prediction_upper)
    if target_transform == "none":
        return upper
    if target_transform == "log":
        return float(np.log(max(upper, 1e-12)))
    if target_transform == "log1p":
        return float(np.log1p(max(upper, -0.999999)))
    raise ValueError(f"Неизвестный target_transform: {target_transform}")


def clip_raw_predictions(raw_pred: np.ndarray, target_transform: str, final_prediction_upper: Optional[float]) -> np.ndarray:
    raw = np.asarray(raw_pred, dtype=np.float64)
    upper = transform_prediction_upper(final_prediction_upper, target_transform=target_transform)
    if upper is None:
        return raw
    return np.clip(raw, a_min=None, a_max=float(upper))


def _metric_from_predictions(y_true: np.ndarray, y_pred: np.ndarray, metric_name: str) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if metric_name == "rmse":
        return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    if metric_name == "mae":
        return float(np.mean(np.abs(y_true - y_pred)))
    if metric_name == "rmsle":
        yt = np.clip(y_true, 0.0, None)
        yp = np.clip(y_pred, 0.0, None)
        return float(np.sqrt(np.mean((np.log1p(yp) - np.log1p(yt)) ** 2)))
    if metric_name == "mape_pct":
        denom = np.maximum(np.abs(y_true), 1e-6)
        return float(np.mean(np.abs(y_pred - y_true) / denom) * 100.0)
    if metric_name == "wape_pct":
        denom = max(float(np.sum(np.abs(y_true))), 1e-6)
        return float(np.sum(np.abs(y_pred - y_true)) / denom * 100.0)
    raise ValueError(f"Неизвестная monitor metric для GNN: {metric_name}")


def train_gnn_model(
    train_graphs_raw: Sequence[Any],
    valid_graphs_raw: Sequence[Any],
    node_onehot_dim: int,
    edge_onehot_dim: int,
    params: Dict[str, Any],
    target_transform: str,
    seed: int,
) -> GNNModelBundle:
    torch, _, F, ReduceLROnPlateau, DataLoader, *_ = _require_torch_modules()
    set_seed(seed)

    device = get_device(params.get("device"))
    norm_stats = fit_norm_stats(train_graphs_raw, node_onehot_dim=node_onehot_dim, edge_onehot_dim=edge_onehot_dim)
    train_graphs = clone_and_normalize_graphs(train_graphs_raw, norm_stats)
    valid_graphs = clone_and_normalize_graphs(valid_graphs_raw, norm_stats)

    y_train_original = extract_graph_targets(train_graphs_raw)
    train_target_max = float(np.max(y_train_original)) if y_train_original.size else np.nan
    prediction_cap_multiplier = float(params.get("prediction_cap_multiplier", 2.0))
    final_prediction_upper: Optional[float] = None
    if np.isfinite(train_target_max) and train_target_max > 0.0 and prediction_cap_multiplier > 0.0:
        final_prediction_upper = float(train_target_max * prediction_cap_multiplier)

    weighted_loss_enabled = bool(params.get("weighted_loss_enabled", True))
    weighted_sampler_enabled = bool(params.get("weighted_sampler_enabled", True))

    loss_weights = make_frequency_weights(
        y_train_original,
        n_bins=int(params.get("weighted_loss_bins", 5)),
        power=float(params.get("weighted_loss_power", 0.5)),
        max_weight=float(params.get("weighted_loss_max_weight", 5.0)),
    ) if weighted_loss_enabled else np.ones(len(train_graphs), dtype=np.float64)

    sampler_weights = make_frequency_weights(
        y_train_original,
        n_bins=int(params.get("weighted_loss_bins", 5)),
        power=float(params.get("weighted_sampler_power", 0.5)),
        max_weight=float(params.get("weighted_sampler_max_weight", 5.0)),
    ) if weighted_sampler_enabled else np.ones(len(train_graphs), dtype=np.float64)

    train_graphs = attach_sample_weights_to_graphs(train_graphs, loss_weights)

    batch_size = int(params.get("batch_size", 24))
    eval_batch_size = int(params.get("eval_batch_size", 64))
    if weighted_sampler_enabled and len(train_graphs) > 0:
        sampler = torch.utils.data.WeightedRandomSampler(
            weights=torch.as_tensor(sampler_weights, dtype=torch.double),
            num_samples=int(len(sampler_weights)),
            replacement=True,
        )
        train_loader = DataLoader(train_graphs, batch_size=batch_size, sampler=sampler, shuffle=False)
    else:
        train_loader = DataLoader(train_graphs, batch_size=batch_size, shuffle=True)
    valid_loader = DataLoader(valid_graphs, batch_size=eval_batch_size, shuffle=False)

    model_kwargs = {
        "node_dim": int(train_graphs[0].x.size(1)),
        "edge_dim": int(train_graphs[0].edge_attr.size(1)),
        "hidden_dim": int(params.get("hidden_dim", 96)),
        "num_layers": int(params.get("num_layers", 4)),
        "dropout": float(params.get("dropout", 0.15)),
        "train_eps": bool(params.get("train_eps", False)),
    }
    model = build_gine_regressor(**model_kwargs).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(params.get("lr", 1e-3)),
        weight_decay=float(params.get("weight_decay", 1e-4)),
    )
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=float(params.get("lr_factor", 0.5)),
        patience=int(params.get("lr_patience", 12)),
    )

    best_metric = float("inf")
    best_state = None
    patience_left = int(params.get("early_stopping_patience", 30))
    min_delta = float(params.get("min_delta", 1e-5))
    epochs = int(params.get("epochs", 300))
    loss_name = str(params.get("loss", "huber"))
    monitor_metric = str(params.get("monitor_metric", "rmsle"))
    grad_clip_norm = float(params.get("grad_clip_norm", 1.0))

    for _epoch in range(1, epochs + 1):
        model.train()
        for batch in train_loader:
            batch = batch.to(device)
            target = transform_target_values(batch.y, target_transform=target_transform)
            optimizer.zero_grad(set_to_none=True)
            pred = model(batch)
            if loss_name == "huber":
                per_sample_loss = F.huber_loss(pred, target, delta=1.0, reduction="none")
            elif loss_name == "l1":
                per_sample_loss = F.l1_loss(pred, target, reduction="none")
            else:
                per_sample_loss = F.mse_loss(pred, target, reduction="none")
            if hasattr(batch, "sample_weight"):
                sample_weight = batch.sample_weight.view(-1).float()
                loss = (per_sample_loss * sample_weight).mean()
            else:
                loss = per_sample_loss.mean()
            loss.backward()
            if grad_clip_norm > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip_norm)
            optimizer.step()

        y_true, y_pred = predict_graphs(
            model,
            valid_graphs,
            norm_stats,
            device=device,
            target_transform=target_transform,
            batch_size=eval_batch_size,
            return_targets=True,
            final_prediction_upper=final_prediction_upper,
        )
        monitor_value = _metric_from_predictions(y_true=y_true, y_pred=y_pred, metric_name=monitor_metric)
        scheduler.step(monitor_value)

        if monitor_value < best_metric - min_delta:
            best_metric = monitor_value
            best_state = copy.deepcopy(model.state_dict())
            patience_left = int(params.get("early_stopping_patience", 30))
        else:
            patience_left -= 1

        if patience_left <= 0:
            break

    if best_state is None:
        best_state = copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state)
    model.eval()
    return GNNModelBundle(
        model=model,
        norm_stats=norm_stats,
        model_kwargs=model_kwargs,
        device=device,
        fit_seed=int(seed),
        raw_prediction_upper=transform_prediction_upper(final_prediction_upper, target_transform=target_transform),
        final_prediction_upper=final_prediction_upper,
    )


def fit_gnn_full_model(
    train_graphs_raw: Sequence[Any],
    node_onehot_dim: int,
    edge_onehot_dim: int,
    params: Dict[str, Any],
    target_transform: str,
    seed: int,
) -> GNNModelBundle:
    return train_gnn_model(
        train_graphs_raw=train_graphs_raw,
        valid_graphs_raw=train_graphs_raw,
        node_onehot_dim=node_onehot_dim,
        edge_onehot_dim=edge_onehot_dim,
        params=params,
        target_transform=target_transform,
        seed=seed,
    )


@np.vectorize

def _identity(x):
    return x


def predict_graphs(
    model: Any,
    graphs_raw: Sequence[Any],
    norm_stats: NormStats,
    device: Any,
    target_transform: str,
    batch_size: int = 64,
    return_targets: bool = False,
    final_prediction_upper: Optional[float] = None,
):
    torch, _, _, _, DataLoader, *_ = _require_torch_modules()
    graphs = clone_and_normalize_graphs(graphs_raw, norm_stats)
    loader = DataLoader(graphs, batch_size=batch_size, shuffle=False)
    model.eval()
    preds_raw: List[np.ndarray] = []
    targets: List[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            pred = model(batch).detach().cpu().numpy().astype(np.float64)
            preds_raw.append(pred)
            if return_targets and hasattr(batch, "y"):
                targets.append(batch.y.view(-1).detach().cpu().numpy().astype(np.float64))
    raw = np.concatenate(preds_raw, axis=0) if preds_raw else np.empty((0,), dtype=np.float64)
    raw = clip_raw_predictions(raw, target_transform=target_transform, final_prediction_upper=final_prediction_upper)
    pred = inverse_target_values(raw, target_transform=target_transform)
    if final_prediction_upper is not None and np.isfinite(final_prediction_upper):
        pred = np.clip(pred, 0.0, float(final_prediction_upper))
    else:
        pred = np.clip(pred, 0.0, None)
    if not return_targets:
        return pred
    y_true = np.concatenate(targets, axis=0) if targets else np.empty((0,), dtype=np.float64)
    return y_true, pred
