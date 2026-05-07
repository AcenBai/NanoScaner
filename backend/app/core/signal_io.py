from __future__ import annotations

import csv
import io
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

ALLOWED_PRESSURE_TYPES = {"positive": "正压", "negative": "负压"}
METADATA_FIELDS = [
    "signal_uid",
    "sample_uid",
    "sample_name",
    "sample_index",
    "pressure_type",
    "pressure_label",
    "original_filename",
    "saved_filename",
    "saved_path",
    "num_points",
    "upload_time",
    "status",
]

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
RAW_DIR = STORAGE_DIR / "raw"
METADATA_DIR = STORAGE_DIR / "metadata"
METADATA_FILE = METADATA_DIR / "signal_files.csv"


def sanitize_field(raw_value: str) -> str:
    sanitized = raw_value.strip()
    sanitized = re.sub(r"\s+", "_", sanitized)
    sanitized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")


def _parse_first_column(file_text: str, file_ext: str) -> list[float]:
    values: list[float] = []

    if file_ext == ".csv":
        reader = csv.reader(io.StringIO(file_text))
        for row in reader:
            if not row:
                continue
            first_col = row[0].strip()
            if not first_col:
                continue
            try:
                values.append(float(first_col))
            except ValueError as exc:
                raise ValueError("The first column cannot be converted to numeric values.") from exc
        return values

    # TXT: support one value per line or multi-column with comma/tab/space separators.
    for line in file_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        tokens = [token for token in re.split(r"[\t,\s]+", stripped) if token]
        if not tokens:
            continue
        try:
            values.append(float(tokens[0]))
        except ValueError as exc:
            raise ValueError("The first column cannot be converted to numeric values.") from exc

    return values


def _parse_abf(file_bytes: bytes) -> list[float]:
    try:
        from neo.io import AxonIO  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "ABF support requires neo. Please install dependencies with pip install -r backend/requirements.txt."
        ) from exc

    with tempfile.NamedTemporaryFile(suffix=".abf", delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        try:
            reader = AxonIO(filename=tmp.name)
            block = reader.read_block()
            segment = block.segments[0]
            signal = segment.analogsignals[0]
            values = [float(v) for v in signal.magnitude.reshape(-1).tolist()]
        except Exception as exc:
            raise ValueError("Unable to parse ABF file.") from exc
    return values


def _ensure_metadata_file() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    if METADATA_FILE.exists():
        return
    with METADATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
        writer.writeheader()


def _metadata_contains_signal_uid(signal_uid: str) -> bool:
    if not METADATA_FILE.exists():
        return False
    with METADATA_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("signal_uid") == signal_uid:
                return True
    return False


def _append_metadata_row(row: dict[str, Any]) -> None:
    with METADATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
        writer.writerow(row)


async def save_uploaded_signal(
    sample_name: str,
    sample_index: str,
    pressure_type: str,
    upload_file: UploadFile,
) -> dict[str, Any]:
    normalized_name = sanitize_field(sample_name)
    normalized_index = sanitize_field(sample_index)

    if not normalized_name:
        raise ValueError("sample_name is required.")
    if not normalized_index:
        raise ValueError("sample_index is required.")
    if pressure_type not in ALLOWED_PRESSURE_TYPES:
        raise ValueError("pressure_type must be one of: positive, negative.")
    if upload_file is None or not upload_file.filename:
        raise ValueError("file is required.")

    file_ext = Path(upload_file.filename).suffix.lower()
    if file_ext not in {".csv", ".txt", ".abf"}:
        raise ValueError("Only CSV, TXT, or ABF files are supported.")

    file_bytes = await upload_file.read()
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    if file_ext == ".abf":
        values = _parse_abf(file_bytes)
    else:
        try:
            file_text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                file_text = file_bytes.decode("gb18030")
            except UnicodeDecodeError as exc:
                raise ValueError("Unable to decode file content with utf-8 or gb18030.") from exc
        values = _parse_first_column(file_text, file_ext)
    if not values:
        raise ValueError("No valid numeric points found in the first column.")

    sample_uid = f"{normalized_name}_{normalized_index}"
    signal_uid = f"{sample_uid}_{pressure_type}"

    _ensure_metadata_file()

    if _metadata_contains_signal_uid(signal_uid):
        raise ValueError(
            f"signal_uid {signal_uid} already exists, please use another sample index "
            "or delete the existing file first."
        )

    saved_filename = f"{signal_uid}{file_ext}"
    save_path = RAW_DIR / saved_filename
    with save_path.open("wb") as f:
        f.write(file_bytes)

    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pressure_label = ALLOWED_PRESSURE_TYPES[pressure_type]
    saved_path = f"backend/app/storage/raw/{saved_filename}"

    result = {
        "signal_uid": signal_uid,
        "sample_uid": sample_uid,
        "sample_name": normalized_name,
        "sample_index": normalized_index,
        "pressure_type": pressure_type,
        "pressure_label": pressure_label,
        "original_filename": upload_file.filename,
        "saved_filename": saved_filename,
        "saved_path": saved_path,
        "num_points": len(values),
        "upload_time": upload_time,
        "status": "success",
    }
    _append_metadata_row(result)
    return result
