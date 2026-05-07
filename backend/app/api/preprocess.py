from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.preprocessing import preprocess_signal, sample_signal_points, save_processed_signal
from ..core.signal_io import list_uploaded_signals, load_raw_signal_values

router = APIRouter()


class PreprocessRequest(BaseModel):
    signal_uid: str


@router.get("/signals")
def get_uploaded_signals() -> dict[str, list[dict[str, str]]]:
    return {"signals": list_uploaded_signals()}


@router.post("/run")
def run_preprocess(request: PreprocessRequest) -> dict:
    signal_uid = request.signal_uid.strip()
    if not signal_uid:
        raise HTTPException(status_code=400, detail="signal_uid is required.")

    try:
        raw_values, metadata = load_raw_signal_values(signal_uid)
        preprocessing_result = preprocess_signal(raw_values)
        processed_values = preprocessing_result["processed"]
        output_path = save_processed_signal(signal_uid, processed_values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preprocess failed: {exc}") from exc

    raw_preview = sample_signal_points(raw_values, max_points=400)
    processed_preview = sample_signal_points(processed_values, max_points=400)

    return {
        "signal_uid": signal_uid,
        "num_raw_points": len(raw_values),
        "num_processed_points": len(processed_values),
        "raw_preview": raw_preview,
        "processed_preview": processed_preview,
        "processed_path": output_path,
        "status": "success",
        "metadata": metadata,
    }


@router.get("/export/{signal_uid}")
def export_preprocessed_signal(signal_uid: str) -> FileResponse:
    output_file = (
        Path(__file__).resolve().parent.parent / "storage" / "processed" / f"{signal_uid}_processed.csv"
    )
    if not output_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"processed result for signal_uid {signal_uid} not found, run preprocess first.",
        )

    return FileResponse(
        path=output_file,
        media_type="text/csv",
        filename=output_file.name,
    )
