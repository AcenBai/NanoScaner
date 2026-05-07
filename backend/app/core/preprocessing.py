from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
import pywt
from scipy import stats
from scipy.signal import savgol_filter

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
PROCESSED_DIR = STORAGE_DIR / "processed"


def wavelet_baseline(
    signal: np.ndarray, wavelet: str = "db4", level: int = 3
) -> tuple[np.ndarray, list[np.ndarray]]:
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    coeffs_for_baseline = coeffs.copy()
    coeffs_for_baseline[1:] = [np.zeros_like(c) for c in coeffs_for_baseline[1:]]
    baseline = pywt.waverec(coeffs_for_baseline, wavelet)
    return baseline[: len(signal)], coeffs


def robust_normalize(values: np.ndarray) -> np.ndarray:
    med = np.median(values)
    iqr = stats.iqr(values)
    if iqr < 1e-8:
        return np.zeros_like(values)
    return (values - med) / (4 * iqr) + 0.5


def signal_normalize_whole(values: np.ndarray) -> np.ndarray:
    centered = values - np.mean(values)
    value_range = np.max(centered) - np.min(centered)
    if abs(value_range) < 1e-12:
        return np.zeros_like(centered)
    return (centered - np.min(centered)) / value_range


def signal_normalize_half(values: np.ndarray) -> np.ndarray:
    value_range = np.max(values) - np.min(values)
    if abs(value_range) < 1e-12:
        return np.zeros_like(values)
    return (values - np.min(values)) / value_range


def _resolve_savgol_params(length: int, window: int, order: int) -> tuple[int, int]:
    if length < 3:
        return 0, 0
    usable_window = min(window, length if length % 2 == 1 else length - 1)
    if usable_window < 3:
        return 0, 0
    usable_order = min(order, usable_window - 1)
    return usable_window, usable_order


def preprocess_signal(
    raw_signal: list[float] | np.ndarray,
    *,
    wavelet: str = "db4",
    level: int = 3,
    sg_window: int = 31,
    sg_order: int = 5,
    clamp_negative: bool = True,
) -> dict[str, Any]:
    signal = np.asarray(raw_signal, dtype=np.float64).reshape(-1)
    if signal.size == 0:
        raise ValueError("raw signal is empty.")

    baseline, _ = wavelet_baseline(signal, wavelet=wavelet, level=level)
    corrected = signal - baseline

    window, order = _resolve_savgol_params(len(corrected), sg_window, sg_order)
    if window and order:
        corrected_sg = savgol_filter(corrected, window, order)
    else:
        corrected_sg = corrected.copy()
    corrected_sg_normalized = signal_normalize_whole(corrected_sg)

    processed = corrected.copy()
    if clamp_negative:
        processed = np.where(processed < 0, 0.0, processed)
    processed = robust_normalize(processed)

    return {
        "raw": signal.tolist(),
        "baseline": baseline.tolist(),
        "corrected": corrected.tolist(),
        "corrected_sg": corrected_sg.tolist(),
        "corrected_sg_normalized": corrected_sg_normalized.tolist(),
        "processed": processed.tolist(),
        "config": {
            "wavelet": wavelet,
            "level": level,
            "sg_window": window,
            "sg_order": order,
            "clamp_negative": clamp_negative,
        },
    }


def sample_signal_points(values: list[float], max_points: int = 400) -> list[float]:
    if len(values) <= max_points:
        return values
    indices = np.linspace(0, len(values) - 1, max_points, dtype=int)
    return np.asarray(values)[indices].tolist()


def save_processed_signal(signal_uid: str, processed_values: list[float]) -> str:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / f"{signal_uid}_processed.csv"

    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["processed_signal"])
        for value in processed_values:
            writer.writerow([value])

    return str(output_file)
