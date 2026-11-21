"""
Shared semantic answer cache in Redis (one entry per question, reused by every user).

Keys
----
* ``answers:q:<hash>``      one cached answer: question, normalised hash as its
                            cache id, answer, sources, embedding vector, the
                            model that generated it, its original tokens and
                            cost, created / last-accessed / expires timestamps,
                            hit count, status.
* ``answers:lock:<hash>``   short-lived generation lock (stampede protection).
* ``answers:stats:stored``  counter of entries ever written, so expired or
                            evicted entries can be estimated as
                            stored - active.

Lookup runs in two stages:

1. Exact match: the normalised question is hashed and read in O(1).
2. Semantic match: the stored questions are scanned and compared by cosine
   similarity of their embeddings (word overlap, Jaccard, when no embedding
   provider is configured). The best candidate above the threshold wins
   (``ANSWERS_SIMILARITY_THRESHOLD``, default 0.92).

Validity rules keep "similar looking" questions apart:

* Numbers, years and dates must match exactly between the two questions
  ("in 2019" is not "in 2020").
* Time markers must match ("today", "yesterday", "latest", "this week").
* Volatile questions (weather, prices, scores, news, anything "current")
  skip the semantic stage entirely and are stored with a short TTL.
* Vectors from a different embedding model are never compared.

Expiry policy (documented, explicit): entries live ``ANSWERS_CACHE_TTL``
seconds (2 h) from their last hit, i.e. a sliding window: every hit rewrites
the entry with a fresh TTL and updates ``last_accessed_at`` and
``expires_at``. Volatile entries use ``ANSWERS_VOLATILE_TTL`` (10 min).
Redis evicts expired keys itself, so an expired answer can never be
returned.

Redis fails open: any Redis error is treated as a cache miss, and
``available()`` lets the caller report the lookup as bypassed rather than as
a miss.
"""
import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Tuple

from app.config import settings
from app.utils.redis_client import RedisClient, redis_client

logger = logging.getLogger(__name__)

KEY_PREFIX = "answers:q:"
LOCK_PREFIX = "answers:lock:"
STORED_COUNTER = "answers:stats:stored"
STATUS_ACTIVE = "active"
_WORD = re.compile(r"[a-z0-9]+")
_NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "who", "how", "why", "when", "where",
    "which", "does", "did", "do", "of", "in", "on", "for", "to", "and", "or", "me", "tell", "about",
    "please", "can", "you", "it", "this", "that", "with", "from", "by",
}
# Words that pin a question to a moment: two questions must agree on them.
_TEMPORAL = {
    "today", "tonight", "yesterday", "tomorrow", "now", "current", "currently", "latest", "recent",
    "recently", "live", "upcoming", "this week", "this month", "this year", "last week", "last month",
    "last year", "right now", "at the moment", "so far",
}
# Topics whose answers change by the hour: never matched semantically, cached only briefly.
_VOLATILE = {
    "weather", "temperature", "forecast", "price", "prices", "stock", "stocks", "share price",
    "exchange rate", "score", "scores", "result", "results", "news", "headline", "headlines",
    "traffic", "schedule", "timetable", "open now", "live", "trending", "today", "tonight",
    "yesterday", "tomorrow", "right now", "currently", "latest",
}


def normalise(question: str) -> str:
    """Lower-case, collapse whitespace and drop trailing punctuation."""
    text = " ".join(question.lower().split())
    return text.rstrip("?!. ")


def question_hash(question: str) -> str:
    return hashlib.sha1(normalise(question).encode("utf-8")).hexdigest()[:20]


def question_key(question: str) -> str:
    return f"{KEY_PREFIX}{question_hash(question)}"


def lock_key(question: str) -> str:
    return f"{LOCK_PREFIX}{question_hash(question)}"


def content_words(question: str) -> set:
    return {w for w in _WORD.findall(question.lower()) if len(w) >= 3 and w not in _STOPWORDS}


def question_signature(question: str) -> Tuple[Set[str], Set[str]]:
    """(numbers, time markers) that two questions must share to mean the same thing."""
    text = " " + normalise(question) + " "
    numbers = {n.strip(".,:/-") for n in _NUMBER.findall(text)}
    markers = {m for m in _TEMPORAL if f" {m} " in text}
    return numbers, markers


def is_volatile(question: str) -> bool:
    """True for questions whose correct answer changes with time."""
    text = " " + normalise(question) + " "
    return any(f" {term} " in text for term in _VOLATILE)


def compatible(a: str, b: str) -> bool:
    """Two questions may share an answer only when their numbers and time markers agree."""
    return question_signature(a) == question_signature(b)


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class CachedAnswer:
    key: str
    question: str
    answer: str
    sources: List[dict] = field(default_factory=list)
    vector: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    created_at: float = 0.0
    last_accessed_at: float = 0.0
    expires_at: float = 0.0
    hits: int = 0
    #: Who generated the stored answer and what it cost once.
    served_model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generation_cost_usd: float = 0.0
    #: "model" (own knowledge) or "crawler" (composed from sources).
    answered_by: str = "crawler"
    status: str = STATUS_ACTIVE

    @property
    def cache_id(self) -> str:
        return self.key.rsplit(":", 1)[-1]

    @classmethod
    def from_redis(cls, key: str, raw: Any) -> Optional["CachedAnswer"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("question"), str):
            return None
        if not isinstance(raw.get("answer"), str):
            return None
        vector = raw.get("vector")
        return cls(
            key=key,
            question=raw["question"],
            answer=raw["answer"],
            sources=[s for s in raw.get("sources", []) if isinstance(s, dict)],
            vector=vector if isinstance(vector, list) and vector else None,
            embedding_model=raw.get("embedding_model"),
            created_at=float(raw.get("created_at") or 0),
            last_accessed_at=float(raw.get("last_accessed_at") or raw.get("created_at") or 0),
            expires_at=float(raw.get("expires_at") or 0),
            hits=int(raw.get("hits") or 0),
            served_model=raw.get("served_model"),
            provider=raw.get("provider"),
            prompt_tokens=int(raw.get("prompt_tokens") or 0),
            completion_tokens=int(raw.get("completion_tokens") or 0),
            generation_cost_usd=float(raw.get("generation_cost_usd") or 0.0),
            answered_by=str(raw.get("answered_by") or "crawler"),
            status=str(raw.get("status") or STATUS_ACTIVE),
        )

    def to_redis(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources,
            "vector": self.vector,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "expires_at": self.expires_at,
            "hits": self.hits,
            "served_model": self.served_model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "generation_cost_usd": self.generation_cost_usd,
            "answered_by": self.answered_by,
            "status": self.status,
        }


@dataclass
class CacheMatch:
    entry: CachedAnswer
    similarity: float
    method: str  # "exact" | "embedding" | "lexical"


@dataclass
class CacheStats:
    active_entries: int
    stored_total: int
    expired_estimate: int
    bytes_used: int
    scanned: int
    total_hits: int
    oldest_created_at: Optional[float]


class SemanticCache:
    def __init__(
        self,
        redis: Optional[RedisClient] = None,
        *,
        threshold: Optional[float] = None,
        lexical_threshold: Optional[float] = None,
        ttl: Optional[int] = None,
        volatile_ttl: Optional[int] = None,
        max_scan: int = 500,
    ):
        self._redis = redis or redis_client
        self.threshold = threshold if threshold is not None else settings.answers_similarity_threshold
        self.lexical_threshold = (
            lexical_threshold if lexical_threshold is not None else settings.answers_lexical_threshold
        )
        self.ttl = ttl if ttl is not None else settings.answers_cache_ttl
        self.volatile_ttl = volatile_ttl if volatile_ttl is not None else settings.answers_volatile_ttl
        self.max_scan = max_scan

    # ----------------------------------------------------------- lookups

    async def available(self) -> bool:
        """False when Redis cannot be reached: lookups are bypassed, not misses."""
        ping = getattr(self._redis, "ping", None)
        if ping is None:
            return True
        return bool(await ping())

    async def get_exact(self, question: str) -> Optional[CachedAnswer]:
        """The entry for exactly this question (normalised), without counting a hit."""
        key = question_key(question)
        return CachedAnswer.from_redis(key, await self._redis.get(key))

    async def find(
        self, question: str, vector: Optional[List[float]], embedding_model: Optional[str] = None
    ) -> Optional[CacheMatch]:
        """Best stored question for ``question``, or None when nothing is close enough."""
        exact_key = question_key(question)
        exact = CachedAnswer.from_redis(exact_key, await self._redis.get(exact_key))
        if exact is not None:
            await self._touch(exact)
            return CacheMatch(entry=exact, similarity=1.0, method="exact")

        if is_volatile(question):
            return None  # only an identical question may reuse a time-sensitive answer

        words = content_words(question)
        best: Optional[CacheMatch] = None
        scanned = 0
        async for key in self._redis.scan_iter(KEY_PREFIX + "*", count=100):
            if key == exact_key:
                continue
            entry = CachedAnswer.from_redis(key, await self._redis.get(key))
            if entry is None or entry.status != STATUS_ACTIVE:
                continue
            scanned += 1
            if not compatible(question, entry.question):
                continue  # different numbers, dates or time markers: not the same question
            same_space = entry.vector is not None and (
                embedding_model is None or entry.embedding_model in (None, embedding_model)
            )
            if vector is not None and same_space:
                similarity, method, floor = cosine(vector, entry.vector), "embedding", self.threshold
            else:
                similarity = jaccard(words, content_words(entry.question))
                method, floor = "lexical", self.lexical_threshold
            if similarity >= floor and (best is None or similarity > best.similarity):
                best = CacheMatch(entry=entry, similarity=similarity, method=method)
            if scanned >= self.max_scan:
                break

        if best is not None:
            await self._touch(best.entry)
        return best

    # ------------------------------------------------------------ writes

    def ttl_for(self, question: str) -> int:
        return self.volatile_ttl if is_volatile(question) else self.ttl

    async def store(
        self,
        question: str,
        vector: Optional[List[float]],
        answer: str,
        sources: List[dict],
        *,
        embedding_model: Optional[str] = None,
        served_model: Optional[str] = None,
        provider: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        generation_cost_usd: float = 0.0,
        answered_by: str = "crawler",
    ) -> CachedAnswer:
        now = time.time()
        ttl = self.ttl_for(question)
        entry = CachedAnswer(
            key=question_key(question),
            question=question.strip(),
            answer=answer,
            sources=sources,
            vector=vector,
            embedding_model=embedding_model if vector is not None else None,
            created_at=now,
            last_accessed_at=now,
            expires_at=now + ttl,
            served_model=served_model,
            provider=provider,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            generation_cost_usd=float(generation_cost_usd),
            answered_by=answered_by,
        )
        if await self._redis.set(entry.key, entry.to_redis(), ttl=ttl):
            await self._redis.increment(STORED_COUNTER)
        return entry

    async def invalidate(self, question: str) -> bool:
        return await self._redis.delete(question_key(question))

    async def _touch(self, entry: CachedAnswer) -> None:
        """Count the hit and slide the expiry (see the module docstring). Best effort."""
        now = time.time()
        ttl = self.ttl_for(entry.question)
        entry.hits += 1
        entry.last_accessed_at = now
        entry.expires_at = now + ttl
        await self._redis.set(entry.key, entry.to_redis(), ttl=ttl)

    # -------------------------------------------------- stampede protection

    async def acquire_generation_lock(self, question: str) -> bool:
        """True when this request should generate; False when another one already is (or Redis failed)."""
        set_nx = getattr(self._redis, "set_if_absent", None)
        if set_nx is None:
            return True
        return await set_nx(lock_key(question), "1", ttl=settings.answers_lock_ttl)

    async def release_generation_lock(self, question: str) -> None:
        await self._redis.delete(lock_key(question))

    async def wait_for_entry(self, question: str, timeout_seconds: float, poll_seconds: float = 0.2) -> Optional[CachedAnswer]:
        """Poll for the exact entry another request is generating; None when it does not appear in time."""
        import asyncio

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_seconds)
            entry = await self.get_exact(question)
            if entry is not None:
                await self._touch(entry)
                return entry
        return None

    # -------------------------------------------------------------- stats

    async def stats(self, max_scan: int = 2000) -> CacheStats:
        """What is in the cache right now: entries, bytes, hits. Expired = stored counter - active (estimate)."""
        active = 0
        bytes_used = 0
        total_hits = 0
        oldest: Optional[float] = None
        scanned = 0
        memory = getattr(self._redis, "memory_usage", None)
        async for key in self._redis.scan_iter(KEY_PREFIX + "*", count=200):
            scanned += 1
            entry = CachedAnswer.from_redis(key, await self._redis.get(key))
            if entry is None:
                continue
            active += 1
            total_hits += entry.hits
            if entry.created_at and (oldest is None or entry.created_at < oldest):
                oldest = entry.created_at
            if memory is not None:
                bytes_used += await memory(key)
            if scanned >= max_scan:
                break
        raw = await self._redis.get(STORED_COUNTER)
        try:
            stored = int(raw or 0)
        except (TypeError, ValueError):
            stored = 0
        return CacheStats(
            active_entries=active,
            stored_total=max(stored, active),
            expired_estimate=max(0, max(stored, active) - active),
            bytes_used=bytes_used,
            scanned=scanned,
            total_hits=total_hits,
            oldest_created_at=oldest,
        )
