from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def report_placeholder() -> dict[str, str]:
    return {"message": "Report generation API placeholder"}
