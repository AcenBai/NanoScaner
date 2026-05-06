from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def ml_placeholder() -> dict[str, str]:
    return {"message": "Machine learning API placeholder"}
