from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def preprocess_placeholder() -> dict[str, str]:
    return {"message": "Signal preprocessing API placeholder"}
