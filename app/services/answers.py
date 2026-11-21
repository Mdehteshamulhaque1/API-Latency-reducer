"""
Answer service: shared semantic cache, then the model's own knowledge, then
Wikipedia, then the other sources; the result is stored for next time.

    question --embed--> SemanticCache.find --hit--> cached answer (exact or semantic)
                                         \\--miss-> generation lock
                                                    model knowledge (UNKNOWN? ->)
                                                    Wikipedia (nothing? ->)
                                                    DuckDuckGo / Wikidata / web search
                                                    -> compose -> SemanticCache.store

Time-sensitive questions skip the model stage, since its knowledge is not
current. ``ANSWERS_MODEL_FIRST=False`` skips it for every question.

The cache is shared by every caller: User A's generated answer serves User
B's identical or similar question. The route records a separate per-request
row for each caller through ``app.services.answer_history`` (database plus
the Redis recent list), so a shared cache hit still produces an individual
record with its own latency and cost.

Cost accounting (all estimates from the pricing tables, never billing):
* embedding cost is charged on every request that embeds the question;
* LLM cost is charged only on generation (misses);
* a hit's ``saved_cost_usd`` = the entry's original generation cost minus
  this request's embedding cost, floored at zero, labelled as an estimate.

Stampede protection: the first request for an uncached question takes a
short Redis lock while it generates; identical concurrent requests wait for
the entry to appear instead of generating again. Redis being unavailable
degrades to "bypassed": no lookup, no lock, normal generation, never a
false hit.

Private questions (anything where the guardrails masked personal data) are
answered but never written to the shared cache (``cacheable=False``).
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from app.ai.answers.composer import SOURCE_MODEL, ComposeFn, ComposeResult, answer_from_knowledge, compose
from app.ai.answers.crawler import Crawler, Page
from app.ai.answers.semantic_cache import CachedAnswer, SemanticCache, is_volatile
from app.ai.rag.embeddings import estimate_tokens, get_embedding_client
from app.config import settings
from app.core.exceptions import ExternalServiceError

WIKIPEDIA = "wikipedia"

CACHE_EXACT_HIT = "exact_hit"
CACHE_SEMANTIC_HIT = "semantic_hit"
CACHE_MISS = "miss"
CACHE_BYPASSED = "bypassed"

logger = logging.getLogger(__name__)

NOT_FOUND = "I could not find anything about that. Try rephrasing the question."


@dataclass
class EmbeddingOutcome:
    vector: Optional[List[float]] = None
    model: Optional[str] = None
    tokens: int = 0
    tokens_estimated: bool = False
    latency_ms: float = 0.0
    cost_usd: float = 0.0


@dataclass
class AnswerResult:
    question: str
    answer: str
    answered_by: str  # "cache" | "model" | "crawler"
    cached: bool
    similarity: Optional[float]
    matched_question: Optional[str]
    sources: List[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    crawl_ms: Optional[float] = None
    compose_method: Optional[str] = None  # "knowledge" | "llm" | "extract"
    embedding_used: bool = False
    match_method: Optional[str] = None  # "exact" | "embedding" | "lexical"
    #: exact_hit | semantic_hit | miss | bypassed (Redis unavailable)
    cache_status: str = CACHE_MISS
    #: Time spent embedding the question and searching the cache.
    cache_lookup_ms: float = 0.0
    embedding_ms: float = 0.0
    embedding_tokens: int = 0
    #: True when the provider reported no embedding usage and the tokens were estimated from text length.
    embedding_tokens_estimated: bool = False
    embedding_model: Optional[str] = None
    #: Model call time and usage when generation used the LLM.
    llm_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    served_model: Optional[str] = None
    #: Costs for THIS request (estimates). ``estimated_cost_usd`` is kept as the total for older readers.
    llm_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0
    #: On a hit: the entry's original generation cost minus this request's embedding cost (estimate).
    saved_cost_usd: float = 0.0
    billable_tokens: int = 0
    cost_inr: float = 0.0
    #: Redis key of the cache entry that answered (hit) or was written (miss); None when not cached.
    cache_key: Optional[str] = None
    cache_id: Optional[str] = None
    #: True when this request waited for another request's generation instead of generating.
    waited_for_generation: bool = False
    volatile: bool = False
    cacheable: bool = True

    @property
    def found(self) -> bool:
        return self.answer != NOT_FOUND

    @property
    def primary_source(self) -> Optional[str]:
        """Provider that answered: the model's own knowledge, or the first page the crawler used."""
        if self.cached:
            return None
        if self.answered_by == "model":
            return SOURCE_MODEL
        if not self.sources:
            return None
        source = self.sources[0].get("source")
        return source if isinstance(source, str) else None


class AnswerService:
    def __init__(
        self,
        *,
        cache: Optional[SemanticCache] = None,
        crawler: Optional[Crawler] = None,
        embedding_factory: Callable = get_embedding_client,
        compose_fn: ComposeFn = compose,
        knowledge_fn: Callable = answer_from_knowledge,
        model_first: Optional[bool] = None,
        lock_wait_seconds: Optional[float] = None,
    ):
        self._cache = cache or SemanticCache()
        self._crawler = crawler or Crawler()
        self._embedding_factory = embedding_factory
        self._compose = compose_fn
        self._knowledge = knowledge_fn
        self.model_first = settings.answers_model_first if model_first is None else model_first
        self.lock_wait_seconds = (
            settings.answers_lock_wait_seconds if lock_wait_seconds is None else lock_wait_seconds
        )

    # ---------------------------------------------------------------- embed

    async def _embed(self, question: str) -> EmbeddingOutcome:
        client = self._embedding_factory()
        if not getattr(client, "configured", False):
            return EmbeddingOutcome()
        started = time.perf_counter()
        try:
            if hasattr(client, "embed_with_usage"):
                result = await client.embed_with_usage([question])
                vector = result.vectors[0] if result.vectors else None
                return EmbeddingOutcome(
                    vector=vector, model=result.model, tokens=result.tokens,
                    tokens_estimated=getattr(result, "tokens_estimated", False),
                    latency_ms=result.latency_ms, cost_usd=result.estimated_cost_usd,
                )
            vectors = await client.embed([question])
        except ExternalServiceError as exc:
            # Embeddings are an optimisation; lexical matching still works without them.
            logger.warning("question embedding unavailable: %s", (exc.details or {}).get("reason", "error"))
            return EmbeddingOutcome(latency_ms=(time.perf_counter() - started) * 1000)
        return EmbeddingOutcome(
            vector=vectors[0] if vectors else None, model=getattr(client, "model", None),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    # --------------------------------------------------------------- answer

    async def answer(
        self,
        question: str,
        *,
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        cacheable: bool = True,
    ) -> AnswerResult:
        started = time.perf_counter()
        question = " ".join(question.split())
        volatile = is_volatile(question)

        redis_up = await self._cache.available()
        embedding = await self._embed(question)
        match = await self._cache.find(question, embedding.vector, embedding.model) if redis_up else None
        cache_lookup_ms = (time.perf_counter() - started) * 1000
        if match is not None:
            return self._from_hit(
                question, match.entry, similarity=match.similarity, method=match.method,
                started=started, embedding=embedding, cache_lookup_ms=cache_lookup_ms,
                volatile=volatile, cacheable=cacheable,
            )

        # Stampede protection: one generator per question; the others wait for its entry.
        locked = False
        waited = False
        if redis_up and cacheable:
            locked = await self._cache.acquire_generation_lock(question)
            if not locked and self.lock_wait_seconds > 0:
                entry = await self._cache.wait_for_entry(question, self.lock_wait_seconds)
                if entry is not None:
                    result = self._from_hit(
                        question, entry, similarity=1.0, method="exact", started=started, embedding=embedding,
                        cache_lookup_ms=(time.perf_counter() - started) * 1000,
                        volatile=volatile, cacheable=cacheable,
                    )
                    result.waited_for_generation = True
                    return result
                waited = True  # the generator did not finish in time: generate anyway

        try:
            result = await self._generate(
                question, started=started, embedding=embedding, cache_lookup_ms=cache_lookup_ms,
                volatile=volatile, cacheable=cacheable, redis_up=redis_up,
                user_id=user_id, correlation_id=correlation_id,
            )
        finally:
            if locked:
                await self._cache.release_generation_lock(question)
        result.waited_for_generation = waited
        return result

    async def _generate(
        self,
        question: str,
        *,
        started: float,
        embedding: EmbeddingOutcome,
        cache_lookup_ms: float,
        volatile: bool,
        cacheable: bool,
        redis_up: bool,
        user_id: Optional[int],
        correlation_id: Optional[str],
    ) -> AnswerResult:
        cache_status = CACHE_MISS if redis_up else CACHE_BYPASSED
        store = cacheable and redis_up

        # Stage 1: the model's own knowledge (never for time-sensitive questions).
        if self.model_first and not volatile:
            known = await self._knowledge(question, correlation_id=correlation_id, user_id=user_id)
            if known is not None:
                entry = await self._store(question, embedding, known, [], "model") if store else None
                return self._from_compose(
                    question, known, [], answered_by="model", started=started, crawl_ms=None,
                    embedding=embedding, cache_lookup_ms=cache_lookup_ms, entry=entry,
                    cache_status=cache_status, volatile=volatile, cacheable=cacheable,
                )

        # Stage 2: Wikipedia; stage 3: the other sources. A source that errors
        # is skipped as long as a later one answers; the first error is raised
        # only when nothing answered at all.
        crawl_started = time.perf_counter()
        pages, error = await self._crawl_in_stages(question)
        crawl_ms = (time.perf_counter() - crawl_started) * 1000
        if not pages and error is not None:
            raise error
        if not pages:
            return AnswerResult(
                question=question,
                answer=NOT_FOUND,
                answered_by="crawler",
                cached=False,
                similarity=None,
                matched_question=None,
                latency_ms=(time.perf_counter() - started) * 1000,
                crawl_ms=crawl_ms,
                embedding_used=embedding.vector is not None,
                cache_status=cache_status,
                cache_lookup_ms=cache_lookup_ms,
                embedding_ms=embedding.latency_ms,
                embedding_tokens=embedding.tokens,
            embedding_tokens_estimated=embedding.tokens_estimated,
                embedding_model=embedding.model,
                embedding_cost_usd=embedding.cost_usd,
                total_cost_usd=embedding.cost_usd,
                estimated_cost_usd=embedding.cost_usd,
                volatile=volatile,
                cacheable=cacheable,
            )

        composed = await self._compose(question, pages, correlation_id=correlation_id, user_id=user_id)
        sources = [{"title": page.title, "url": page.url, "source": page.source} for page in pages]
        entry = await self._store(question, embedding, composed, sources, "crawler") if store else None
        return self._from_compose(
            question, composed, sources, answered_by="crawler", started=started, crawl_ms=crawl_ms,
            embedding=embedding, cache_lookup_ms=cache_lookup_ms, entry=entry,
            cache_status=cache_status, volatile=volatile, cacheable=cacheable,
        )

    async def _store(
        self, question: str, embedding: EmbeddingOutcome, composed: ComposeResult, sources: List[dict], answered_by: str
    ) -> CachedAnswer:
        return await self._cache.store(
            question, embedding.vector, composed.answer, sources,
            embedding_model=embedding.model,
            served_model=composed.served_model,
            provider=settings.llm_provider,
            prompt_tokens=composed.prompt_tokens,
            completion_tokens=composed.completion_tokens,
            generation_cost_usd=composed.estimated_cost_usd,
            answered_by=answered_by,
        )

    async def _crawl_in_stages(self, question: str) -> tuple[List[Page], Optional[ExternalServiceError]]:
        """Wikipedia first, then the remaining configured sources; (pages, first error)."""
        configured = list(self._crawler.sources)
        stages = [[s] for s in configured if s == WIKIPEDIA] + [[s for s in configured if s != WIKIPEDIA]]
        first_error: Optional[ExternalServiceError] = None
        for stage in stages:
            if not stage:
                continue
            try:
                pages = await self._crawler.crawl(question, sources=stage)
            except ExternalServiceError as exc:
                logger.warning("answer stage %s failed: %s", "+".join(stage), (exc.details or {}).get("reason"))
                first_error = first_error or exc
                continue
            if pages:
                return pages, None
        return [], first_error

    # ------------------------------------------------------------- results

    @staticmethod
    def _from_hit(
        question: str,
        entry: CachedAnswer,
        *,
        similarity: float,
        method: str,
        started: float,
        embedding: EmbeddingOutcome,
        cache_lookup_ms: float,
        volatile: bool,
        cacheable: bool,
    ) -> AnswerResult:
        saved = max(0.0, entry.generation_cost_usd - embedding.cost_usd)
        return AnswerResult(
            question=question,
            answer=entry.answer,
            answered_by="cache",
            cached=True,
            similarity=round(similarity, 4),
            matched_question=entry.question,
            sources=entry.sources,
            latency_ms=(time.perf_counter() - started) * 1000,
            embedding_used=embedding.vector is not None,
            match_method=method,
            cache_status=CACHE_EXACT_HIT if method == "exact" else CACHE_SEMANTIC_HIT,
            cache_lookup_ms=cache_lookup_ms,
            embedding_ms=embedding.latency_ms,
            embedding_tokens=embedding.tokens,
            embedding_tokens_estimated=embedding.tokens_estimated,
            embedding_model=embedding.model,
            served_model=entry.served_model,
            llm_cost_usd=0.0,
            embedding_cost_usd=embedding.cost_usd,
            total_cost_usd=embedding.cost_usd,
            estimated_cost_usd=embedding.cost_usd,
            saved_cost_usd=round(saved, 10),
            billable_tokens=0,
            cost_inr=0.0,
            cache_key=entry.key,
            cache_id=entry.cache_id,
            volatile=volatile,
            cacheable=cacheable,
        )

    @staticmethod
    def _from_compose(
        question: str,
        composed: ComposeResult,
        sources: List[dict],
        *,
        answered_by: str,
        started: float,
        crawl_ms: Optional[float],
        embedding: EmbeddingOutcome,
        cache_lookup_ms: float,
        entry: Optional[CachedAnswer],
        cache_status: str,
        volatile: bool,
        cacheable: bool,
    ) -> AnswerResult:
        total = composed.estimated_cost_usd + embedding.cost_usd
        # Every non-cached answer is charged. When no model tokens were used
        # (page-extract fallback), the answer's own tokens are estimated.
        billable_tokens = max(0, int(composed.total_tokens)) or estimate_tokens(composed.answer)
        cost_inr = round(billable_tokens * settings.answers_inr_per_token, 2)
        return AnswerResult(
            question=question,
            answer=composed.answer,
            answered_by=answered_by,
            cached=False,
            similarity=None,
            matched_question=None,
            sources=sources,
            latency_ms=(time.perf_counter() - started) * 1000,
            crawl_ms=crawl_ms,
            compose_method=composed.method,
            embedding_used=embedding.vector is not None,
            cache_status=cache_status,
            cache_lookup_ms=cache_lookup_ms,
            embedding_ms=embedding.latency_ms,
            embedding_tokens=embedding.tokens,
            embedding_tokens_estimated=embedding.tokens_estimated,
            embedding_model=embedding.model,
            llm_ms=composed.llm_ms,
            prompt_tokens=composed.prompt_tokens,
            completion_tokens=composed.completion_tokens,
            total_tokens=composed.total_tokens,
            served_model=composed.served_model,
            llm_cost_usd=composed.estimated_cost_usd,
            embedding_cost_usd=embedding.cost_usd,
            total_cost_usd=round(total, 10),
            estimated_cost_usd=round(total, 10),
            billable_tokens=billable_tokens,
            cost_inr=cost_inr,
            cache_key=entry.key if entry else None,
            cache_id=entry.cache_id if entry else None,
            volatile=volatile,
            cacheable=cacheable,
        )


def get_answer_service() -> AnswerService:
    """Factory used by the route; tests replace it with fakes."""
    return AnswerService()
