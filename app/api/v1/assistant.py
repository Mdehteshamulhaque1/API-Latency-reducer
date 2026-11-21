"""
Assistant routes.

POST /assistant/ask                   performance questions over measured facts
GET  /assistant/suggested-questions   starter prompts for the dashboard
GET  /assistant/cache-recommendations advisory caching analysis
POST /assistant/troubleshoot          evidence-based diagnosis for errors and slowness
"""
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.engine import AssistantService
from app.ai.assistant.recommendations import analyse, explain
from app.ai.assistant.troubleshoot import TroubleshootService
from app.core.security import get_current_user
from app.database.db import get_session
from app.schemas.assistant import (
    AssistantAskRequest,
    AssistantAskResponse,
    KnownCause,
    RecommendationItem,
    RecommendationResponse,
    SuggestedQuestions,
    TroubleshootRequest,
    TroubleshootResponse,
)
from app.schemas.documents import SourceChunk

router = APIRouter(prefix="/assistant", tags=["Assistant"])

SUGGESTED_QUESTIONS = [
    "Which endpoint has the highest p95 latency?",
    "Which endpoint receives the most requests?",
    "What is my current cache hit ratio and is it good enough?",
    "Why might the slowest endpoint be slow?",
    "How many requests were rate limited and on which endpoints?",
    "What should I investigate first to improve performance?",
    "How much have LLM calls cost in the last 24 hours?",
    "Explain my API performance statistics in plain language.",
]


def _identity(current_user: dict) -> tuple[int, bool]:
    return int(current_user.get("sub")), current_user.get("role") == "admin"


@router.get("/suggested-questions", response_model=SuggestedQuestions)
async def suggested_questions(current_user: dict = Depends(get_current_user)):
    return SuggestedQuestions(questions=SUGGESTED_QUESTIONS)


@router.post("/ask", response_model=AssistantAskResponse)
async def ask_assistant(
    payload: AssistantAskRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id, is_admin = _identity(current_user)
    result = await AssistantService(session).ask(
        payload.question,
        hours=payload.hours,
        user_id=user_id,
        is_admin=is_admin,
        correlation_id=getattr(request.state, "correlation_id", None),
        include_docs=payload.include_docs,
        service=payload.service,
    )
    data = asdict(result)
    data["sources"] = [SourceChunk(**vars(chunk)) for chunk in result.sources]
    return AssistantAskResponse(**data)


@router.get("/cache-recommendations", response_model=RecommendationResponse)
async def cache_recommendations(
    request: Request,
    hours: int = Query(default=24, gt=0, le=720),
    narrative: bool = Query(default=True, description="Ask the model for a short explanation"),
    service: Optional[str] = Query(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id, is_admin = _identity(current_user)
    report = await analyse(session, user_id=None if is_admin else user_id, hours=hours, service=service)
    if narrative:
        report = await explain(
            report, user_id=user_id, correlation_id=getattr(request.state, "correlation_id", None)
        )
    return RecommendationResponse(
        hours=report.hours,
        analysed_endpoints=report.analysed_endpoints,
        recommendations=[RecommendationItem(**asdict(r)) for r in report.recommendations],
        explanation=report.explanation,
        llm_available=report.llm_available,
        note=report.note,
    )


@router.post("/troubleshoot", response_model=TroubleshootResponse)
async def troubleshoot(
    payload: TroubleshootRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id, is_admin = _identity(current_user)
    report = await TroubleshootService(session).run(
        status_code=payload.status_code,
        endpoint=payload.endpoint,
        symptom=payload.symptom,
        hours=payload.hours,
        user_id=user_id,
        is_admin=is_admin,
        correlation_id=getattr(request.state, "correlation_id", None),
        service=payload.service,
    )
    return TroubleshootResponse(
        status_code=report.status_code,
        endpoint=report.endpoint,
        symptom=report.symptom,
        hours=report.hours,
        evidence=report.evidence,
        known_causes=[KnownCause(**c) for c in report.known_causes],
        sources=[SourceChunk(**vars(chunk)) for chunk in report.sources],
        explanation=report.explanation,
        llm_available=report.llm_available,
        model=report.model,
        estimated_cost_usd=report.estimated_cost_usd,
    )
