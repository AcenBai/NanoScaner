from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold

from .feature_extraction import DEFAULT_FEATURE_LIBRARY, build_inference_feature_row_from_signal
from .report_generator import generate_report_artifacts

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
MODELS_DIR = STORAGE_DIR / "models"
REPORTS_DIR = STORAGE_DIR / "reports"
MODEL_REGISTRY_FILE = MODELS_DIR / "model_registry.json"
LATEST_RUN_FILE = MODELS_DIR / "latest_run.json"
DEFAULT_FOLDS = 10
DEFAULT_SEED = 2018
DEFAULT_MODEL_PARAMS = {
    "iterations": 2000,
    "learning_rate": 0.05,
    "depth": 8,
    "l2_leaf_reg": 1.0,
    "random_seed": DEFAULT_SEED,
    "loss_function": "Logloss",
    "verbose": 0,
}
NON_FEATURE_COLUMNS = {
    "label",
    "source",
    "source_minus",
    "样本",
    "样本_minus",
    "signal_uid",
    "sample_uid",
}


def _ensure_storage_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _to_serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_serializable(v) for v in value]
    if isinstance(value, tuple):
        return [_to_serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def _default_group_column(df: pd.DataFrame) -> pd.Series:
    if "sample_uid" in df.columns:
        group = df["sample_uid"].astype(str)
        if group.str.strip().ne("").any():
            return group
    if "样本" in df.columns:
        group = df["样本"].astype(str)
        if group.str.strip().ne("").any():
            return group
    if "样本_minus" in df.columns:
        group = df["样本_minus"].astype(str)
        if group.str.strip().ne("").any():
            return group
    return pd.Series(df.index.astype(str), index=df.index)


def _load_default_feature_dataset() -> pd.DataFrame:
    if not DEFAULT_FEATURE_LIBRARY.exists():
        raise ValueError(f"default feature library not found: {DEFAULT_FEATURE_LIBRARY}")
    return pd.read_csv(DEFAULT_FEATURE_LIBRARY)


def _prepare_training_data(
    df: pd.DataFrame,
    *,
    negative_label: str | None = None,
    positive_label: str | None = None,
) -> tuple[pd.DataFrame, np.ndarray, pd.Series, dict[str, int], list[str], dict[str, Any]]:
    if "label" not in df.columns:
        raise ValueError("default feature library must contain label column.")

    label_series = df["label"].astype(str).str.strip()
    valid_mask = label_series != ""
    df = df.loc[valid_mask].copy()
    label_series = label_series.loc[valid_mask]
    unique_labels = sorted(label_series.unique().tolist())
    selected_mode = "direct_binary"
    if negative_label and positive_label:
        selected_mode = "selected_two_labels"
        mask = (label_series == negative_label) | (label_series == positive_label)
        df = df.loc[mask].copy()
        label_series = label_series.loc[mask]
        if label_series.empty:
            raise ValueError("no rows left after applying positive_label / negative_label filter.")
        mapped_labels = label_series.copy()
        labels_sorted = [negative_label, positive_label]
    elif len(unique_labels) == 2:
        labels_sorted = unique_labels
        mapped_labels = label_series.copy()
    elif "健康对照" in unique_labels:
        selected_mode = "healthy_vs_all_sick"
        labels_sorted = ["健康对照", "其他疾病"]
        mapped_labels = label_series.apply(lambda x: "健康对照" if x == "健康对照" else "其他疾病")
    else:
        raise ValueError(
            "default feature library has more than 2 labels; please provide positive_label and negative_label."
        )

    label_to_int = {name: idx for idx, name in enumerate(labels_sorted)}
    y = mapped_labels.map(label_to_int).to_numpy(dtype=int)
    groups = _default_group_column(df)

    feature_columns: list[str] = []
    for col in df.columns:
        if col in NON_FEATURE_COLUMNS:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() == 0:
            continue
        df[col] = numeric
        feature_columns.append(col)

    if not feature_columns:
        raise ValueError("no valid numeric feature columns found.")

    x = df[feature_columns].copy()
    medians = x.median(numeric_only=True)
    x = x.fillna(medians).fillna(0.0)
    label_config = {
        "mode": selected_mode,
        "negative_label": labels_sorted[0],
        "positive_label": labels_sorted[1],
    }
    return x, y, groups, label_to_int, feature_columns, label_config


def _aggregate_bag_results(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    groups: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    bag_true: dict[str, int] = {}
    bag_preds: dict[str, list[int]] = defaultdict(list)
    bag_probs: dict[str, list[np.ndarray]] = defaultdict(list)

    for true_label, pred_label, probs, group_name in zip(y_true, y_pred, y_prob, groups):
        key = str(group_name)
        bag_true[key] = int(true_label)
        bag_preds[key].append(int(pred_label))
        bag_probs[key].append(np.asarray(probs, dtype=float))

    final_true: list[int] = []
    final_pred_hard: list[int] = []
    final_pred_soft: list[int] = []
    final_prob: list[np.ndarray] = []
    bag_soft_map: dict[str, int] = {}
    for bag_name in bag_preds.keys():
        probs_arr = np.vstack(bag_probs[bag_name])
        vote_counter = Counter(bag_preds[bag_name])
        hard = vote_counter.most_common(1)[0][0]
        mean_prob = probs_arr.mean(axis=0)
        soft = int(np.argmax(mean_prob))

        final_true.append(bag_true[bag_name])
        final_pred_hard.append(int(hard))
        final_pred_soft.append(int(soft))
        final_prob.append(mean_prob)
        bag_soft_map[bag_name] = int(soft)

    return (
        np.asarray(final_true, dtype=int),
        np.asarray(final_pred_hard, dtype=int),
        np.asarray(final_pred_soft, dtype=int),
        np.vstack(final_prob),
        bag_soft_map,
    )


def _build_metrics_result(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    groups: np.ndarray,
    label_names: list[str],
) -> dict[str, Any]:
    def _binary_metrics_from_cm(cm: list[list[int]]) -> dict[str, float]:
        arr = np.asarray(cm, dtype=float)
        if arr.shape != (2, 2):
            return {
                "sensitivity": 0.0,
                "specificity": 0.0,
                "precision": 0.0,
                "f1": 0.0,
            }
        tn, fp, fn, tp = arr.ravel()
        sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1 = float(2 * precision * sensitivity / (precision + sensitivity)) if (precision + sensitivity) > 0 else 0.0
        return {
            "sensitivity": sensitivity,
            "specificity": specificity,
            "precision": precision,
            "f1": f1,
        }

    bag_true, bag_pred_hard, bag_pred_soft, bag_probas, bag_soft_map = _aggregate_bag_results(
        y_true, y_pred, y_prob, groups
    )
    sample_soft = np.asarray([bag_soft_map[str(group)] for group in groups], dtype=int)

    sample_auc = roc_auc_score(y_true, y_prob[:, 1]) if len(np.unique(y_true)) == 2 else 0.0
    bag_auc = roc_auc_score(bag_true, bag_probas[:, 1]) if len(np.unique(bag_true)) == 2 else 0.0
    fpr, tpr, _ = roc_curve(bag_true, bag_probas[:, 1])

    sample_cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    bag_cm = confusion_matrix(bag_true, bag_pred_hard, labels=[0, 1]).tolist()
    sample_extra = _binary_metrics_from_cm(sample_cm)
    bag_extra = _binary_metrics_from_cm(bag_cm)

    return {
        "sample": {
            "accuracy_hard": float(accuracy_score(y_true, y_pred)),
            "accuracy_soft": float(accuracy_score(y_true, sample_soft)),
            "classification_report_hard": classification_report(
                y_true,
                y_pred,
                labels=[0, 1],
                target_names=label_names,
                output_dict=True,
                zero_division=0,
            ),
            "classification_report_soft": classification_report(
                y_true,
                sample_soft,
                labels=[0, 1],
                target_names=label_names,
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix_hard": sample_cm,
            "auc": float(sample_auc),
            **sample_extra,
        },
        "bag": {
            "accuracy_hard": float(accuracy_score(bag_true, bag_pred_hard)),
            "accuracy_soft": float(accuracy_score(bag_true, bag_pred_soft)),
            "classification_report_hard": classification_report(
                bag_true,
                bag_pred_hard,
                labels=[0, 1],
                target_names=label_names,
                output_dict=True,
                zero_division=0,
            ),
            "classification_report_soft": classification_report(
                bag_true,
                bag_pred_soft,
                labels=[0, 1],
                target_names=label_names,
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix_hard": bag_cm,
            "auc_soft": float(bag_auc),
            "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
            "bag_true": bag_true.tolist(),
            "bag_pred_hard": bag_pred_hard.tolist(),
            "bag_pred_soft": bag_pred_soft.tolist(),
            "bag_probas": bag_probas.tolist(),
            **bag_extra,
        },
    }


def _load_registry() -> dict[str, Any]:
    if not MODEL_REGISTRY_FILE.exists():
        return {"models": []}
    with MODEL_REGISTRY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(data: dict[str, Any]) -> None:
    with MODEL_REGISTRY_FILE.open("w", encoding="utf-8") as f:
        json.dump(_to_serializable(data), f, ensure_ascii=False, indent=2)


def _persist_latest_run(run_id: str) -> None:
    with LATEST_RUN_FILE.open("w", encoding="utf-8") as f:
        json.dump({"run_id": run_id}, f, ensure_ascii=False, indent=2)


def get_latest_run_id() -> str | None:
    if not LATEST_RUN_FILE.exists():
        return None
    with LATEST_RUN_FILE.open("r", encoding="utf-8") as f:
        return json.load(f).get("run_id")


def get_default_training_dataset_summary() -> dict[str, Any]:
    df = _load_default_feature_dataset()
    label_counts = (
        df["label"].astype(str).str.strip().replace("", np.nan).dropna().value_counts().to_dict()
        if "label" in df.columns
        else {}
    )
    groups = _default_group_column(df)
    return {
        "dataset_path": str(DEFAULT_FEATURE_LIBRARY),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "unique_samples": int(groups.nunique()),
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "unique_labels": sorted(label_counts.keys()),
    }


def train_binary_model(config: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_storage_dirs()
    cfg = dict(DEFAULT_MODEL_PARAMS)
    request_cfg = config or {}
    cfg.update(
        {
            "iterations": int(request_cfg.get("iterations", cfg["iterations"])),
            "learning_rate": float(request_cfg.get("learning_rate", cfg["learning_rate"])),
            "depth": int(request_cfg.get("depth", cfg["depth"])),
            "l2_leaf_reg": float(request_cfg.get("l2_leaf_reg", cfg["l2_leaf_reg"])),
            "random_seed": int(request_cfg.get("random_seed", cfg["random_seed"])),
            "verbose": 0,
            "loss_function": "Logloss",
        }
    )
    n_splits = int(request_cfg.get("n_splits", DEFAULT_FOLDS))
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")

    df = _load_default_feature_dataset()
    x, y, groups, label_to_int, feature_columns, label_config = _prepare_training_data(
        df,
        negative_label=request_cfg.get("negative_label"),
        positive_label=request_cfg.get("positive_label"),
    )
    if groups.nunique() < n_splits:
        n_splits = int(groups.nunique())
    if n_splits < 2:
        raise ValueError("not enough unique samples for GroupKFold.")

    gkf = GroupKFold(n_splits=n_splits)
    oof_pred = np.zeros(len(x), dtype=int)
    oof_prob = np.zeros((len(x), len(label_to_int)), dtype=float)

    for train_idx, test_idx in gkf.split(x, y, groups=groups):
        model = CatBoostClassifier(**cfg)
        model.fit(x.iloc[train_idx], y[train_idx])
        fold_pred = model.predict(x.iloc[test_idx]).reshape(-1)
        fold_proba = model.predict_proba(x.iloc[test_idx])
        oof_pred[test_idx] = fold_pred.astype(int)
        oof_prob[test_idx] = fold_proba

    int_to_label = {v: k for k, v in label_to_int.items()}
    label_names = [int_to_label[idx] for idx in sorted(int_to_label.keys())]
    metrics = _build_metrics_result(
        y_true=y,
        y_pred=oof_pred,
        y_prob=oof_prob,
        groups=groups.to_numpy(),
        label_names=label_names,
    )

    final_model = CatBoostClassifier(**cfg)
    final_model.fit(x, y)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    model_path = MODELS_DIR / f"{run_id}_catboost.cbm"
    final_model.save_model(str(model_path))

    importance = final_model.get_feature_importance()
    feature_importance = sorted(
        [{"feature": feature_columns[i], "importance": float(importance[i])} for i in range(len(feature_columns))],
        key=lambda row: row["importance"],
        reverse=True,
    )

    run_report_dir = REPORTS_DIR / run_id
    run_report_dir.mkdir(parents=True, exist_ok=True)
    metrics_payload = {
        "run_id": run_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task": "binary_classification",
        "dataset_path": str(DEFAULT_FEATURE_LIBRARY),
        "feature_columns": feature_columns,
        "label_to_int": label_to_int,
        "int_to_label": int_to_label,
        "n_splits": n_splits,
        "label_config": label_config,
        "model_params": cfg,
        "metrics": metrics,
        "feature_importance": feature_importance,
    }
    metrics_path = run_report_dir / "metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(_to_serializable(metrics_payload), f, ensure_ascii=False, indent=2)

    report_artifacts = generate_report_artifacts(metrics_payload, run_report_dir)

    meta = {
        "run_id": run_id,
        "model_type": "CatBoostClassifier",
        "created_at": metrics_payload["created_at"],
        "dataset_path": str(DEFAULT_FEATURE_LIBRARY),
        "feature_columns": feature_columns,
        "label_to_int": label_to_int,
        "int_to_label": int_to_label,
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "report_dir": str(run_report_dir),
        "report_artifacts": report_artifacts,
        "summary": {
            "bag_auc_soft": metrics["bag"]["auc_soft"],
            "bag_accuracy_soft": metrics["bag"]["accuracy_soft"],
            "sample_accuracy_hard": metrics["sample"]["accuracy_hard"],
        },
    }
    meta_path = MODELS_DIR / f"{run_id}_meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(_to_serializable(meta), f, ensure_ascii=False, indent=2)

    registry = _load_registry()
    registry_models = registry.get("models", [])
    registry_models.append(
        {
            "run_id": run_id,
            "created_at": meta["created_at"],
            "model_path": str(model_path),
            "meta_path": str(meta_path),
            "summary": meta["summary"],
        }
    )
    registry["models"] = registry_models
    _save_registry(registry)
    _persist_latest_run(run_id)

    return {
        "status": "success",
        "run_id": run_id,
        "model_path": str(model_path),
        "meta_path": str(meta_path),
        "metrics_path": str(metrics_path),
        "summary": meta["summary"],
        "report_artifacts": report_artifacts,
    }


def list_trained_models() -> list[dict[str, Any]]:
    registry = _load_registry()
    models = registry.get("models", [])
    return list(reversed(models))


def get_model_meta(run_id: str) -> dict[str, Any]:
    meta_path = MODELS_DIR / f"{run_id}_meta.json"
    if not meta_path.exists():
        raise ValueError(f"model run_id {run_id} does not exist.")
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_evaluation(run_id: str | None = None) -> dict[str, Any]:
    target_run = run_id or get_latest_run_id()
    if not target_run:
        raise ValueError("no trained model found.")
    meta = get_model_meta(target_run)
    metrics_path = Path(meta["metrics_path"])
    if not metrics_path.exists():
        raise ValueError(f"metrics file missing for run_id {target_run}.")
    with metrics_path.open("r", encoding="utf-8") as f:
        metrics_data = json.load(f)
    return {"run_id": target_run, "meta": meta, "metrics": metrics_data}


def _build_feature_vector(
    feature_columns: list[str],
    *,
    feature_payload: dict[str, Any] | None = None,
    signal_uid: str | None = None,
) -> pd.DataFrame:
    row: dict[str, Any] = {}
    if signal_uid:
        row = build_inference_feature_row_from_signal(signal_uid)
    if feature_payload:
        row.update(feature_payload)
    vector = {name: float(row.get(name, 0.0)) for name in feature_columns}
    return pd.DataFrame([vector])


def predict_with_trained_model(
    run_id: str,
    *,
    feature_payload: dict[str, Any] | None = None,
    signal_uid: str | None = None,
) -> dict[str, Any]:
    if not run_id:
        raise ValueError("run_id is required.")
    if not feature_payload and not signal_uid:
        raise ValueError("either feature_payload or signal_uid is required.")

    meta = get_model_meta(run_id)
    model = CatBoostClassifier()
    model.load_model(meta["model_path"])
    feature_columns = meta.get("feature_columns", [])
    if not feature_columns:
        raise ValueError("model metadata has no feature_columns.")

    x_pred = _build_feature_vector(
        feature_columns=feature_columns, feature_payload=feature_payload, signal_uid=signal_uid
    )
    probabilities = model.predict_proba(x_pred)[0]
    pred_idx = int(np.argmax(probabilities))
    int_to_label = {int(k): v for k, v in meta.get("int_to_label", {}).items()}
    pred_label = int_to_label.get(pred_idx, str(pred_idx))
    return {
        "run_id": run_id,
        "pred_index": pred_idx,
        "pred_label": pred_label,
        "probabilities": [float(v) for v in probabilities],
        "signal_uid": signal_uid or "",
        "status": "success",
    }
