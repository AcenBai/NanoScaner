from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..core.signal_io import save_uploaded_signal

router = APIRouter()


@router.post("/upload")
async def upload_signal(
    sample_name: str = Form(...),
    sample_index: str = Form(...),
    pressure_type: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if not sample_name or not sample_name.strip():
        raise HTTPException(status_code=400, detail="sample_name is required.")
    if not sample_index or not sample_index.strip():
        raise HTTPException(status_code=400, detail="sample_index is required.")
    if not pressure_type or not pressure_type.strip():
        raise HTTPException(status_code=400, detail="pressure_type is required.")

    try:
        return await save_uploaded_signal(
            sample_name=sample_name,
            sample_index=sample_index,
            pressure_type=pressure_type.strip(),
            upload_file=file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc
