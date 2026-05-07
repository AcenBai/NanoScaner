from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.ml_pipeline import (
    get_default_training_dataset_summary,
    get_evaluation,
    get_latest_run_id,
    list_trained_models,
    predict_with_trained_model,
    train_binary_model,
)

router = APIRouter()


class TrainRequest(BaseModel):
    n_splits: int = Field(default=10, ge=2)
    iterations: int = Field(default=2000, ge=10)
    learning_rate: float = Field(default=0.05, gt=0)
    depth: int = Field(default=8, ge=2)
    l2_leaf_reg: float = Field(default=1.0, gt=0)
    random_seed: int = Field(default=2018)
    negative_label: str | None = None
    positive_label: str | None = None


class PredictRequest(BaseModel):
    run_id: str
    signal_uid: str | None = None
    feature_payload: dict[str, Any] | None = None


@router.get("/dataset-summary")
def dataset_summary() -> dict:
    try:
        return get_default_training_dataset_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read default dataset summary: {exc}") from exc


@router.post("/train")
def train_model(request: TrainRequest) -> dict:
    try:
        return train_binary_model(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Train failed: {exc}") from exc


@router.get("/models")
def get_models() -> dict:
    return {"models": list_trained_models(), "latest_run_id": get_latest_run_id()}


@router.get("/status")
def model_status() -> dict:
    latest = get_latest_run_id()
    if not latest:
        return {"trained": False, "message": "no trained model yet"}
    return {"trained": True, "latest_run_id": latest}


@router.get("/evaluation")
def model_evaluation(run_id: str | None = None) -> dict:
    try:
        return get_evaluation(run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation load failed: {exc}") from exc


@router.post("/predict")
def predict(request: PredictRequest) -> dict:
    try:
        return predict_with_trained_model(
            run_id=request.run_id.strip(),
            signal_uid=request.signal_uid.strip() if request.signal_uid else None,
            feature_payload=request.feature_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc
