from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, savgol_filter, welch

from .preprocessing import robust_normalize, signal_normalize_whole, wavelet_baseline
from .signal_io import read_signal_metadata

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
PROCESSED_DIR = STORAGE_DIR / "processed"
FEATURES_DIR = STORAGE_DIR / "features"
EXTRACTED_FEATURES_FILE = FEATURES_DIR / "extracted_features.csv"
DEFAULT_FEATURE_LIBRARY = Path(__file__).resolve().parents[3] / "df_feature_default.csv"

BASE_FEATURE_COLUMNS = [
    "peak_count",
    "peak_mean",
    "peak_std",
    "signal_std",
    "signal_skew",
    "signal_kurtosis",
    "signal_median",
    "rms",
    "hjorth_activity",
    "hjorth_mobility",
    "hjorth_complexity",
    "kfd",
    "dominant_freq1",
    "dominant_freq2",
    "dominant_freq3",
    "spectral_entropy",
    "total_power",
    "max_power",
    "dominant_freq1_Wel",
    "dominant_freq2_Wel",
    "dominant_freq3_Wel",
    "spectral_entropy_Wel",
    "total_power_Wel",
    "max_power_Wel",
    "spectral_centroid",
    "wavelet_energy",
    "wavelet_subband1",
    "wavelet_subband2",
    "wavelet_subband3",
]


def _safe_float(value: float) -> float:
    return float(np.nan_to_num(value, nan=0.0, posinf=0.0, neginf=0.0))


def _ensure_processed_signal_exists(signal_uid: str) -> Path:
    file_path = PROCESSED_DIR / f"{signal_uid}_processed.csv"
    if not file_path.exists():
        raise ValueError(
            f"processed signal file not found for {signal_uid}, please run preprocess first."
        )
    return file_path


def _load_raw_signal_from_metadata(signal_uid: str, metadata: dict[str, str]) -> np.ndarray:
    saved_filename = metadata.get("saved_filename", "")
    if not saved_filename:
        raise ValueError(f"saved raw filename is missing for {signal_uid}.")

    raw_path = STORAGE_DIR / "raw" / saved_filename
    if not raw_path.exists():
        raise ValueError(f"raw signal file not found for {signal_uid}: {raw_path}")

    values: list[float] = []
    suffix = raw_path.suffix.lower()
    if suffix == ".abf":
        try:
            from neo.io import AxonIO  # type: ignore
        except ImportError as exc:
            raise ValueError(
                "ABF support requires neo. Please install backend dependencies."
            ) from exc
        reader = AxonIO(filename=str(raw_path))
        block = reader.read_block()
        segment = block.segments[0]
        signal = segment.analogsignals[0]
        values = [float(v) for v in signal.magnitude.reshape(-1).tolist()]
    else:
        with raw_path.open("r", encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                first = stripped.split(",")[0].split("\t")[0].split(" ")[0].strip()
                if not first:
                    continue
                try:
                    values.append(float(first))
                except ValueError:
                    continue
    if not values:
        raise ValueError(f"raw signal {signal_uid} has no numeric points.")
    return np.asarray(values, dtype=np.float64)


def _katz_fractal_dimension(signal: np.ndarray) -> float:
    dists = np.abs(np.diff(signal))
    ll = np.sum(dists)
    if ll <= 0:
        return 0.0
    avg_dist = np.mean(dists)
    if avg_dist <= 0:
        return 0.0
    d_max = np.max(np.abs(signal - np.roll(signal, 1)))
    if d_max <= 0:
        return 0.0
    return _safe_float(np.log10(ll) / (np.log10(d_max) + np.log10(avg_dist)))


def _build_notebook_style_series(
    raw_signal: np.ndarray,
    *,
    pressure_type: str,
    wavelet: str = "db4",
    level: int = 3,
    sg_window: int = 31,
    sg_order: int = 5,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    signal = raw_signal.copy()
    if pressure_type == "negative":
        # Notebook's process_abf_file supports isminus=True by multiplying signal by -1.
        signal = signal * (-1.0)

    baseline, coeffs = wavelet_baseline(signal, wavelet=wavelet, level=level)
    corrected = signal - baseline
    corrected_sg = signal_normalize_whole(savgol_filter(corrected, sg_window, sg_order))
    processed = np.where(corrected < 0, 0.0, corrected)
    processed = robust_normalize(processed)
    return processed, corrected_sg, coeffs


def _extract_base_features(
    processed: np.ndarray,
    corrected_sg: np.ndarray,
    coeffs: list[np.ndarray],
    *,
    fs: float = 5e5,
    fft_interval: float = 2e-6,
) -> dict[str, float]:
    peaks, _ = find_peaks(processed, height=0.5)

    features: dict[str, float] = {
        "peak_count": _safe_float(len(peaks)),
        "peak_mean": _safe_float(np.mean(processed[peaks]) if len(peaks) > 0 else 0.0),
        "peak_std": _safe_float(np.std(processed[peaks]) if len(peaks) > 0 else 0.0),
        "signal_std": _safe_float(np.std(processed)),
        "signal_skew": _safe_float(stats.skew(processed)),
        "signal_kurtosis": _safe_float(stats.kurtosis(processed)),
        "signal_median": _safe_float(np.median(corrected_sg)),
        "rms": _safe_float(np.sqrt(np.mean(np.square(corrected_sg)))),
    }

    activity = np.var(corrected_sg)
    diff1 = np.gradient(corrected_sg)
    diff2 = np.gradient(diff1)
    var_diff1 = np.var(diff1)
    mobility = np.sqrt(var_diff1 / activity) if activity > 0 else 0.0
    complexity = (
        (np.sqrt(np.var(diff2) / var_diff1) / mobility) if var_diff1 > 0 and mobility > 0 else 0.0
    )
    features.update(
        {
            "hjorth_activity": _safe_float(activity),
            "hjorth_mobility": _safe_float(mobility),
            "hjorth_complexity": _safe_float(complexity),
            "kfd": _katz_fractal_dimension(corrected_sg),
        }
    )

    n = len(corrected_sg)
    yf = fft(corrected_sg)
    xf = fftfreq(n, fft_interval)[: n // 2]
    magnitudes = np.abs(yf[: n // 2]) * 2 / n
    sorted_indices = np.argsort(magnitudes)[::-1]
    top_indices = sorted_indices[:3]
    features.update(
        {
            "dominant_freq1": _safe_float(xf[top_indices[0]] if len(top_indices) > 0 else 0.0),
            "dominant_freq2": _safe_float(xf[top_indices[1]] if len(top_indices) > 1 else 0.0),
            "dominant_freq3": _safe_float(xf[top_indices[2]] if len(top_indices) > 2 else 0.0),
            "spectral_entropy": _safe_float(-np.sum(magnitudes * np.log(magnitudes + 1e-10))),
            "total_power": _safe_float(np.sum(magnitudes**2)),
            "max_power": _safe_float(np.max(magnitudes**2) if magnitudes.size else 0.0),
        }
    )

    nperseg = min(1024, len(corrected_sg))
    if nperseg < 8:
        freqs = np.array([0.0])
        psd = np.array([0.0])
    else:
        freqs, psd = welch(corrected_sg, fs=fs, nperseg=nperseg)
    sorted_psd = np.argsort(psd)[::-1]
    top_psd = sorted_psd[:3]
    psd_sum = np.sum(psd)
    spectral_centroid = np.sum(freqs * psd) / psd_sum if psd_sum > 0 else 0.0
    psd_prob = psd / psd_sum if psd_sum > 0 else np.zeros_like(psd)
    features.update(
        {
            "dominant_freq1_Wel": _safe_float(freqs[top_psd[0]] if len(top_psd) > 0 else 0.0),
            "dominant_freq2_Wel": _safe_float(freqs[top_psd[1]] if len(top_psd) > 1 else 0.0),
            "dominant_freq3_Wel": _safe_float(freqs[top_psd[2]] if len(top_psd) > 2 else 0.0),
            "spectral_entropy_Wel": _safe_float(-np.sum(psd_prob * np.log(psd_prob + 1e-10))),
            "total_power_Wel": _safe_float(psd_sum),
            "max_power_Wel": _safe_float(np.max(psd) if psd.size else 0.0),
            "spectral_centroid": _safe_float(spectral_centroid),
        }
    )

    features.update(
        {
            "wavelet_energy": _safe_float(np.sum(np.square(coeffs[-1]))),
            "wavelet_subband1": _safe_float(np.sum(np.square(coeffs[0]))),
            "wavelet_subband2": _safe_float(np.sum(np.square(coeffs[1]))),
            "wavelet_subband3": _safe_float(np.sum(np.square(coeffs[2]))),
        }
    )
    return features


def _build_feature_row(
    signal_uid: str,
    metadata: dict[str, str],
    label: str,
    base_features: dict[str, float],
) -> dict[str, Any]:
    pressure_type = metadata.get("pressure_type", "")
    sample_uid = metadata.get("sample_uid", "")
    sample_name = metadata.get("sample_name", "") + metadata.get("sample_index", "")
    processed_source = str(PROCESSED_DIR / f"{signal_uid}_processed.csv")

    row: dict[str, Any] = {"signal_uid": signal_uid, "sample_uid": sample_uid, "label": label}
    is_negative = pressure_type == "negative"
    suffix = "_minus" if is_negative else ""

    for feature_name in BASE_FEATURE_COLUMNS:
        row[f"{feature_name}{suffix}"] = base_features.get(feature_name, 0.0)

    row[f"source{suffix}"] = processed_source
    row[f"样本{suffix}"] = sample_name or sample_uid
    return row


def _append_row_to_csv(file_path: Path, row: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        with file_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        return

    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        existing_fields = reader.fieldnames or []

    new_fields = existing_fields[:]
    for key in row.keys():
        if key not in new_fields:
            new_fields.append(key)

    existing_rows.append({field: row.get(field, "") for field in new_fields})
    normalized_rows = [
        {field: record.get(field, "") for field in new_fields} for record in existing_rows
    ]
    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(normalized_rows)


def list_processed_signals() -> list[dict[str, str]]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, str]] = []
    for file_path in sorted(PROCESSED_DIR.glob("*_processed.csv")):
        signal_uid = file_path.stem.replace("_processed", "")
        try:
            metadata = read_signal_metadata(signal_uid)
        except ValueError:
            metadata = {}
        items.append(
            {
                "signal_uid": signal_uid,
                "file_name": file_path.name,
                "file_path": str(file_path),
                "pressure_type": metadata.get("pressure_type", ""),
                "sample_uid": metadata.get("sample_uid", ""),
            }
        )
    return items


def extract_features_from_processed_signal(signal_uid: str, label: str) -> dict[str, Any]:
    normalized_uid = signal_uid.strip()
    normalized_label = label.strip()
    if not normalized_uid:
        raise ValueError("signal_uid is required.")
    if not normalized_label:
        raise ValueError("label is required.")

    _ensure_processed_signal_exists(normalized_uid)
    metadata = read_signal_metadata(normalized_uid)
    raw_signal = _load_raw_signal_from_metadata(normalized_uid, metadata)
    processed, corrected_sg, coeffs = _build_notebook_style_series(
        raw_signal,
        pressure_type=metadata.get("pressure_type", ""),
    )
    base_features = _extract_base_features(processed, corrected_sg, coeffs)
    feature_row = _build_feature_row(normalized_uid, metadata, normalized_label, base_features)
    _append_row_to_csv(EXTRACTED_FEATURES_FILE, feature_row)

    return {
        "signal_uid": normalized_uid,
        "label": normalized_label,
        "pressure_type": metadata.get("pressure_type", ""),
        "saved_to": str(EXTRACTED_FEATURES_FILE),
        "feature_count": len(base_features),
        "status": "success",
        "feature_row": feature_row,
    }


def build_inference_feature_row_from_signal(signal_uid: str) -> dict[str, float]:
    normalized_uid = signal_uid.strip()
    if not normalized_uid:
        raise ValueError("signal_uid is required.")

    _ensure_processed_signal_exists(normalized_uid)
    metadata = read_signal_metadata(normalized_uid)
    raw_signal = _load_raw_signal_from_metadata(normalized_uid, metadata)
    processed, corrected_sg, coeffs = _build_notebook_style_series(
        raw_signal,
        pressure_type=metadata.get("pressure_type", ""),
    )
    base_features = _extract_base_features(processed, corrected_sg, coeffs)
    is_negative = metadata.get("pressure_type", "") == "negative"
    suffix = "_minus" if is_negative else ""
    row: dict[str, float] = {}
    for feature_name in BASE_FEATURE_COLUMNS:
        row[f"{feature_name}{suffix}"] = float(base_features.get(feature_name, 0.0))
    return row


def get_extracted_features_summary() -> dict[str, Any]:
    if not EXTRACTED_FEATURES_FILE.exists():
        return {"exists": False, "rows": 0, "path": str(EXTRACTED_FEATURES_FILE)}

    with EXTRACTED_FEATURES_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []
    return {
        "exists": True,
        "rows": len(rows),
        "columns": fields,
        "path": str(EXTRACTED_FEATURES_FILE),
    }


def get_default_feature_library_visualization_data() -> dict[str, Any]:
    if not DEFAULT_FEATURE_LIBRARY.exists():
        raise ValueError(f"default feature library not found: {DEFAULT_FEATURE_LIBRARY}")

    target_features = [
        "peak_count",
        "dominant_freq2_Wel",
        "wavelet_subband1",
        "hjorth_mobility",
    ]
    feature_values: dict[str, dict[str, list[float]]] = {
        feature: defaultdict(list) for feature in target_features
    }
    sample_label_map: dict[str, str] = {}

    with DEFAULT_FEATURE_LIBRARY.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = (row.get("label") or "").strip()
            if not label:
                continue

            sample_name = (row.get("样本") or row.get("样本_minus") or "").strip()
            if sample_name and sample_name not in sample_label_map:
                sample_label_map[sample_name] = label

            for feature_name in target_features:
                value_text = (row.get(feature_name) or "").strip()
                if not value_text:
                    continue
                try:
                    feature_values[feature_name][label].append(float(value_text))
                except ValueError:
                    continue

    label_counts: dict[str, int] = defaultdict(int)
    for label in sample_label_map.values():
        label_counts[label] += 1

    boxplots: dict[str, list[dict[str, Any]]] = {}
    for feature_name, by_label in feature_values.items():
        feature_stats: list[dict[str, Any]] = []
        for label, values in by_label.items():
            if not values:
                continue
            arr = np.asarray(values, dtype=np.float64)
            feature_stats.append(
                {
                    "label": label,
                    "count": int(arr.size),
                    "min": _safe_float(np.min(arr)),
                    "q1": _safe_float(np.quantile(arr, 0.25)),
                    "median": _safe_float(np.quantile(arr, 0.5)),
                    "q3": _safe_float(np.quantile(arr, 0.75)),
                    "max": _safe_float(np.max(arr)),
                }
            )
        boxplots[feature_name] = feature_stats

    return {
        "library_path": str(DEFAULT_FEATURE_LIBRARY),
        "unique_sample_count": len(sample_label_map),
        "label_value_counts_by_sample": dict(sorted(label_counts.items())),
        "boxplots": boxplots,
    }
