from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def signal_placeholder() -> dict[str, str]:
    return {"message": "Signal upload/read API placeholder"}
