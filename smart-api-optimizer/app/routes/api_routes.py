from fastapi import APIRouter

from app.services.analyzer import analyze_api

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/analyze")
def analyze() -> dict:
    result = analyze_api()
    return {"message": "Analysis complete", "result": result}
