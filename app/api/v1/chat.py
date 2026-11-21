"""
LLM chat gateway endpoints.

Request flow:
    guardrails screen (injection scan, PII masking)
      -> ChatService (cache, retries, fallback, circuit breaker)
      -> response + X-LLM-* headers
      -> background: ai_request_logs row + guardrail_events rows

The route stays thin; everything it calls is testable on its own.
"""
import time

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.ai.guardrails import screen_messages
from app.ai.guardrails.events import record_events
from app.core.exceptions import APIException, ExternalServiceError
from app.core.security import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_usage import record_chat_error, record_chat_result
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["LLM"])


@router.post("", response_model=ChatResponse)
async def create_chat_completion(
    payload: ChatRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Create a chat completion for the authenticated caller."""
    user_id = None
    subject = current_user.get("sub")
    if subject is not None:
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            user_id = None

    correlation_id = getattr(request.state, "correlation_id", None)
    started = time.perf_counter()

    # 1. Guardrails: never send unscreened text to the provider.
    screen = screen_messages(
        payload.messages, feature="chat", user_id=user_id, correlation_id=correlation_id
    )
    if screen.blocked:
        await record_events(screen.events)
        raise APIException(
            message=screen.block_reason or "Request blocked by guardrails",
            status_code=400,
            error_code="GUARDRAIL_BLOCKED",
            details={"rules": screen.injection_rules},
        )
    if screen.events:
        background_tasks.add_task(record_events, screen.events)

    screened_payload = payload.model_copy(update={"messages": screen.messages})

    # 2. Gateway call.
    try:
        result = await ChatService().create_chat_completion(
            screened_payload,
            user_id=user_id,
            correlation_id=correlation_id,
        )
    except ExternalServiceError as exc:
        # Record the failure once the error response has gone out. Nothing
        # sensitive is stored: only a short reason code and timing.
        background_tasks.add_task(
            record_chat_error,
            requested_model=payload.model,
            user_id=user_id,
            correlation_id=correlation_id,
            latency_ms=(time.perf_counter() - started) * 1000,
            details=exc.details,
        )
        # Starlette only runs background tasks attached to a response, so
        # flush them here before the exception handler builds the error reply.
        await background_tasks()
        raise

    # 3. Usage accounting after the response is sent.
    background_tasks.add_task(
        record_chat_result,
        result,
        requested_model=payload.model,
        user_id=user_id,
        correlation_id=correlation_id,
    )

    request.state.cache_hit = result.cached
    response.headers["X-LLM-Latency-Ms"] = f"{result.latency_ms:.2f}"
    response.headers["X-LLM-Cached"] = "true" if result.cached else "false"
    if screen.pii_counts:
        response.headers["X-Guardrail-PII-Masked"] = str(sum(screen.pii_counts.values()))
    if screen.injection_severity != "none":
        response.headers["X-Guardrail-Injection"] = screen.injection_severity
    return result
