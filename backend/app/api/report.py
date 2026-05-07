from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core.report_generator import export_report_bundle, get_latest_report_summary

router = APIRouter()


@router.get("/latest")
def latest_report(run_id: str | None = None) -> dict:
    try:
        return get_latest_report_summary(run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Load report failed: {exc}") from exc


@router.get("/export")
def export_report(run_id: str) -> FileResponse:
    try:
        bundle = export_report_bundle(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export report failed: {exc}") from exc

    return FileResponse(
        path=bundle,
        media_type="application/zip",
        filename=bundle.name,
    )


@router.get("/file")
def get_report_file(run_id: str, name: str) -> FileResponse:
    report_dir = Path(__file__).resolve().parent.parent / "storage" / "reports" / run_id
    file_path = report_dir / name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"report file not found: {name}")
    return FileResponse(path=file_path, filename=file_path.name)
