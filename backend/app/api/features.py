from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.feature_extraction import (
    EXTRACTED_FEATURES_FILE,
    extract_features_from_processed_signal,
    get_default_feature_library_visualization_data,
    get_extracted_features_summary,
    list_processed_signals,
)

router = APIRouter()


class ExtractFeaturesRequest(BaseModel):
    signal_uid: str
    label: str


@router.get("/processed-signals")
def get_processed_signals() -> dict:
    return {"signals": list_processed_signals()}


@router.post("/extract")
def extract_features(request: ExtractFeaturesRequest) -> dict:
    try:
        return extract_features_from_processed_signal(
            signal_uid=request.signal_uid,
            label=request.label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feature extraction failed: {exc}") from exc


@router.get("/export")
def export_features() -> FileResponse:
    if not EXTRACTED_FEATURES_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="No extracted feature file found, run feature extraction first.",
        )
    return FileResponse(
        path=EXTRACTED_FEATURES_FILE,
        media_type="text/csv",
        filename=EXTRACTED_FEATURES_FILE.name,
    )


@router.get("/summary")
def features_summary() -> dict:
    return get_extracted_features_summary()


@router.get("/visualization/default")
def default_feature_visualization() -> dict:
    try:
        return get_default_feature_library_visualization_data()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Visualization data build failed: {exc}") from exc
