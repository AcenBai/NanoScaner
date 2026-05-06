from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def feature_placeholder() -> dict[str, str]:
    return {"message": "Feature extraction API placeholder"}
