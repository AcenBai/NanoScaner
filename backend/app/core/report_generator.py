from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
REPORTS_DIR = STORAGE_DIR / "reports"


def _save_roc_plot(fpr: list[float], tpr: list[float], auc: float, output_file: Path) -> None:
    plt.figure(figsize=(5, 4), dpi=150)
    plt.plot(fpr, tpr, label=f"AUC={auc:.4f}", linewidth=2)
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Bag-level ROC")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)
    plt.close()


def _save_confusion_plot(cm: list[list[int]], output_file: Path) -> None:
    arr = np.asarray(cm, dtype=float)
    plt.figure(figsize=(4.6, 4.2), dpi=150)
    plt.imshow(arr, cmap="Blues")
    plt.colorbar()
    plt.xticks([0, 1], ["Pred 0", "Pred 1"])
    plt.yticks([0, 1], ["True 0", "True 1"])
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            plt.text(j, i, int(arr[i, j]), ha="center", va="center", color="black")
    plt.title("Bag-level Confusion Matrix")
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)
    plt.close()


def _save_radar_plot(metrics: dict[str, float], output_file: Path) -> None:
    keys = ["AUC", "ACC", "Sensitivity", "Specificity", "Precision", "F1"]
    values = [float(metrics.get(k, 0.0)) for k in keys]
    values = [min(max(v, 0.0), 1.0) for v in values]
    angles = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    angles += angles[:1]
    values += values[:1]

    plt.figure(figsize=(5, 5), dpi=150)
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(keys)
    ax.set_title("Bag-level Radar Metrics")
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)
    plt.close()


def _save_feature_importance_plot(feature_importance: list[dict[str, Any]], output_file: Path) -> None:
    top = feature_importance[:15]
    names = [item["feature"] for item in top][::-1]
    values = [float(item["importance"]) for item in top][::-1]
    plt.figure(figsize=(7, 5), dpi=150)
    plt.barh(names, values)
    plt.xlabel("Importance")
    plt.title("Top 15 Feature Importance")
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)
    plt.close()


def generate_report_artifacts(metrics_payload: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = metrics_payload["metrics"]
    bag = metrics["bag"]

    report_summary = {
        "run_id": metrics_payload.get("run_id"),
        "created_at": metrics_payload.get("created_at"),
        "dataset_path": metrics_payload.get("dataset_path"),
        "bag_auc_soft": bag.get("auc_soft"),
        "bag_accuracy_soft": bag.get("accuracy_soft"),
        "sample_accuracy_hard": metrics["sample"].get("accuracy_hard"),
        "label_mapping": metrics_payload.get("label_to_int", {}),
        "model_params": metrics_payload.get("model_params", {}),
    }
    report_json = output_dir / "report_summary.json"
    with report_json.open("w", encoding="utf-8") as f:
        json.dump(report_summary, f, ensure_ascii=False, indent=2)

    roc_file = output_dir / "roc_test.png"
    _save_roc_plot(
        bag.get("roc_curve", {}).get("fpr", []),
        bag.get("roc_curve", {}).get("tpr", []),
        float(bag.get("auc_soft", 0.0)),
        roc_file,
    )

    cm_file = output_dir / "confusion_matrix_bag.png"
    _save_confusion_plot(bag.get("confusion_matrix_hard", [[0, 0], [0, 0]]), cm_file)

    cm = np.asarray(bag.get("confusion_matrix_hard", [[0, 0], [0, 0]]), dtype=float)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        sensitivity_from_cm = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        specificity_from_cm = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        precision_from_cm = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1_from_cm = (
            float(2 * precision_from_cm * sensitivity_from_cm / (precision_from_cm + sensitivity_from_cm))
            if (precision_from_cm + sensitivity_from_cm) > 0
            else 0.0
        )
    else:
        sensitivity_from_cm = 0.0
        specificity_from_cm = 0.0
        precision_from_cm = 0.0
        f1_from_cm = 0.0

    radar_metrics = {
        "AUC": float(bag.get("auc_soft", 0.0)),
        "ACC": float(bag.get("accuracy_soft", 0.0)),
        "Sensitivity": float(bag.get("sensitivity", sensitivity_from_cm)),
        "Specificity": float(bag.get("specificity", specificity_from_cm)),
        "Precision": float(bag.get("precision", precision_from_cm)),
        "F1": float(bag.get("f1", f1_from_cm)),
    }
    radar_file = output_dir / "radar_metrics.png"
    _save_radar_plot(radar_metrics, radar_file)

    radar_raw_csv = output_dir / "radar_metrics_raw.csv"
    pd.DataFrame([radar_metrics]).to_csv(radar_raw_csv, index=False)
    radar_plot_csv = output_dir / "radar_metrics_plot.csv"
    pd.DataFrame([radar_metrics]).to_csv(radar_plot_csv, index=False)
    radar_ci_csv = output_dir / "radar_metrics_with_95ci.csv"
    ci_df = pd.DataFrame(
        [
            {"metric": key, "value": value, "ci_low": np.nan, "ci_high": np.nan}
            for key, value in radar_metrics.items()
        ]
    )
    ci_df.to_csv(radar_ci_csv, index=False)

    fi_file = output_dir / "feature_importance_top15.png"
    _save_feature_importance_plot(metrics_payload.get("feature_importance", []), fi_file)

    return {
        "report_summary_json": str(report_json),
        "roc_test_png": str(roc_file),
        "confusion_png": str(cm_file),
        "radar_png": str(radar_file),
        "radar_metrics_raw_csv": str(radar_raw_csv),
        "radar_metrics_plot_csv": str(radar_plot_csv),
        "radar_metrics_ci_csv": str(radar_ci_csv),
        "feature_importance_png": str(fi_file),
    }


def get_latest_report_summary(run_id: str | None = None) -> dict[str, Any]:
    target = run_id
    if not target:
        report_dirs = sorted([p for p in REPORTS_DIR.glob("*") if p.is_dir()])
        if not report_dirs:
            raise ValueError("no report available.")
        target = report_dirs[-1].name
    report_dir = REPORTS_DIR / target
    summary_file = report_dir / "report_summary.json"
    metrics_file = report_dir / "metrics.json"
    if not summary_file.exists():
        raise ValueError(f"report summary not found for run_id {target}.")
    with summary_file.open("r", encoding="utf-8") as f:
        summary = json.load(f)
    metrics_data = {}
    if metrics_file.exists():
        with metrics_file.open("r", encoding="utf-8") as f:
            metrics_data = json.load(f)
        # Re-generate artifacts to keep plots in sync with latest metric logic.
        generate_report_artifacts(metrics_data, report_dir)
    return {"run_id": target, "report_dir": str(report_dir), "summary": summary, "metrics": metrics_data}


def export_report_bundle(run_id: str) -> Path:
    report_dir = REPORTS_DIR / run_id
    if not report_dir.exists():
        raise ValueError(f"report directory not found for run_id {run_id}.")
    bundle_path = report_dir / f"{run_id}_report_bundle.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in report_dir.glob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.name)
    return bundle_path
