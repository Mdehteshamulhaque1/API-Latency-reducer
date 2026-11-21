"""
Turn crawled pages into an answer.

With an LLM configured (OPENAI_API_KEY, which may be a Gemini key behind the
OpenAI-compatible endpoint) the model is asked to answer using only the
crawled text, citing sources by number. Without one, or when the model call
fails, the best page's introduction is returned as the answer so the
pipeline still works end to end.

Every model call is recorded in ``ai_request_logs`` under the ``answers``
feature and attributed to the gateway account that asked, so tokens and
estimated cost show up on the AI usage page and can be copied onto the
per-question record.
"""
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

from app.ai.answers.crawler import Page
from app.ai.provider import get_chat_service
from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.ai_usage import record_chat_error, record_chat_result

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You answer questions using only the numbered sources provided. "
    "If the sources do not contain the answer, say that you could not find it. "
    "Be concise: at most six sentences. Cite the sources you used like [1]."
)
CONTEXT_CHARS_PER_PAGE = 2500
EXTRACT_CHARS = 1200
FEATURE = "answers"
SOURCE_MODEL = "gemini"

KNOWLEDGE_PROMPT = (
    "Answer the question from your own knowledge, concisely, in at most five sentences. "
    "If you are not certain, if the answer could have changed recently, or if the question needs "
    "live data (weather, prices, scores, news, schedules), reply with exactly the single word UNKNOWN "
    "and nothing else. Never guess."
)
UNKNOWN = "UNKNOWN"


@dataclass
class ComposeResult:
    answer: str
    #: "llm" when a model wrote the answer from the pages, "extract" when the page intro was used.
    method: str
    llm_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    served_model: Optional[str] = None
    fallback_used: bool = False


ComposeFn = Callable[..., Awaitable[ComposeResult]]


def _context(pages: List[Page]) -> str:
    return "\n\n".join(f"[{i}] {page.title}\n{page.text[:CONTEXT_CHARS_PER_PAGE]}" for i, page in enumerate(pages, 1))


def extract_answer(pages: List[Page]) -> str:
    """Fallback: the first two paragraphs of the best page."""
    page = pages[0]
    paragraphs = [p.strip() for p in page.text.split("\n") if p.strip()]
    text = " ".join(paragraphs[:2])[:EXTRACT_CHARS].rstrip()
    return f"{text}\n\nSource: {page.title} [1]"


async def compose(
    question: str,
    pages: List[Page],
    *,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None,
    chat_service_factory=None,
) -> ComposeResult:
    """Answer from the pages with the model when configured, else from the best page's intro."""
    factory = chat_service_factory or get_chat_service  # resolved at call time so tests can patch it
    if settings.openai_api_key:
        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=f"Question: {question}\n\nSources:\n{_context(pages)}"),
            ],
            temperature=0,
            max_tokens=settings.answers_max_tokens,
        )
        started = time.perf_counter()
        try:
            result = await factory().create_chat_completion(
                request, user_id=user_id, correlation_id=correlation_id
            )
        except ExternalServiceError as exc:
            await record_chat_error(
                requested_model=request.model,
                user_id=user_id,
                correlation_id=correlation_id,
                latency_ms=(time.perf_counter() - started) * 1000,
                details=exc.details,
                feature=FEATURE,
            )
            logger.warning(
                "answer composer fell back to extract: %s", (exc.details or {}).get("reason", "llm_error")
            )
        else:
            await record_chat_result(
                result, requested_model=request.model, user_id=user_id, correlation_id=correlation_id, feature=FEATURE
            )
            answer = result.content.strip()
            if answer:
                return ComposeResult(
                    answer=answer,
                    method="llm",
                    llm_ms=result.latency_ms,
                    prompt_tokens=0 if result.cached else result.usage.prompt_tokens,
                    completion_tokens=0 if result.cached else result.usage.completion_tokens,
                    total_tokens=0 if result.cached else result.usage.total_tokens,
                    estimated_cost_usd=0.0 if result.cached else result.estimated_cost_usd,
                    served_model=result.served_model or result.model,
                    fallback_used=result.fallback_used,
                )
    return ComposeResult(answer=extract_answer(pages), method="extract")


async def answer_from_knowledge(
    question: str,
    *,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None,
    chat_service_factory=None,
) -> Optional[ComposeResult]:
    """Ask the model directly, before any source is read.

    Returns the answer, or None when no model is configured, the call failed,
    or the model answered UNKNOWN (so the caller moves on to the sources).
    """
    if not settings.openai_api_key:
        return None
    factory = chat_service_factory or get_chat_service
    request = ChatRequest(
        messages=[
            ChatMessage(role="system", content=KNOWLEDGE_PROMPT),
            ChatMessage(role="user", content=question),
        ],
        temperature=0,
        max_tokens=settings.answers_max_tokens,
    )
    started = time.perf_counter()
    try:
        result = await factory().create_chat_completion(request, user_id=user_id, correlation_id=correlation_id)
    except ExternalServiceError as exc:
        await record_chat_error(
            requested_model=request.model,
            user_id=user_id,
            correlation_id=correlation_id,
            latency_ms=(time.perf_counter() - started) * 1000,
            details=exc.details,
            feature=FEATURE,
        )
        logger.warning("model-first answer unavailable: %s", (exc.details or {}).get("reason", "llm_error"))
        return None
    await record_chat_result(
        result, requested_model=request.model, user_id=user_id, correlation_id=correlation_id, feature=FEATURE
    )
    answer = result.content.strip()
    if not answer or answer.strip(" .!").upper() == UNKNOWN or answer.upper().startswith(UNKNOWN):
        return None
    return ComposeResult(
        answer=answer,
        method="knowledge",
        llm_ms=result.latency_ms,
        prompt_tokens=0 if result.cached else result.usage.prompt_tokens,
        completion_tokens=0 if result.cached else result.usage.completion_tokens,
        total_tokens=0 if result.cached else result.usage.total_tokens,
        estimated_cost_usd=0.0 if result.cached else result.estimated_cost_usd,
        served_model=result.served_model or result.model,
        fallback_used=result.fallback_used,
    )
