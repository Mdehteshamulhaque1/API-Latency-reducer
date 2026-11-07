"""
LLM chat gateway endpoints.
"""
from fastapi import APIRouter, Depends, Request, Response

from app.core.security import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["LLM"])


@router.post("", response_model=ChatResponse)
async def create_chat_completion(
    payload: ChatRequest,
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Create an OpenAI chat completion for the authenticated caller."""
    user_id = None
    subject = current_user.get("sub")
    if subject is not None:
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            user_id = None

    result = await ChatService().create_chat_completion(
        payload,
        user_id=user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    request.state.cache_hit = result.cached
    response.headers["X-LLM-Latency-Ms"] = f"{result.latency_ms:.2f}"
    response.headers["X-LLM-Cached"] = "true" if result.cached else "false"
    return result
