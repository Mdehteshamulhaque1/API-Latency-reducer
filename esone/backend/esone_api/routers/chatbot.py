"""Public project chatbot: questions about API Optimizer, Esone and the developer.

No account needed, so it is rate limited per client IP with its own sliding
window (ESONE_CHATBOT_RATE_LIMIT_PER_MINUTE), separate from the login limiter.
"""
from fastapi import APIRouter, HTTPException, Request, status

from esone_api.chatbot import get_chatbot
from esone_api.config import get_settings
from esone_api.ratelimit import WINDOW_SECONDS, SlidingWindow, client_ip
from esone_api.schemas import ChatbotRequest, ChatbotResponse

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

chatbot_limiter = SlidingWindow()


@router.post("", response_model=ChatbotResponse)
async def ask_chatbot(data: ChatbotRequest, request: Request) -> ChatbotResponse:
    limit = get_settings().chatbot_rate_limit_per_minute
    if limit > 0:
        wait = chatbot_limiter.check(f"chatbot:{client_ip(request)}", limit)
        if wait:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many messages. Try again in {wait} seconds",
                headers={"Retry-After": str(wait), "RateLimit-Policy": f"{limit};w={WINDOW_SECONDS}"},
            )
    history = [(turn.role, turn.content) for turn in data.history]
    reply = await get_chatbot().reply(data.message.strip(), history)
    return ChatbotResponse(answer=reply.answer, answered_by=reply.answered_by)
