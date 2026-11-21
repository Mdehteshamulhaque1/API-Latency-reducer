"""
Embedding client for any OpenAI-compatible ``/embeddings`` endpoint.

An embedding turns a piece of text into a list of numbers (a vector) such
that texts with similar meaning end up close together. We never compare
words; we compare vectors with cosine similarity, which is what makes
"how do I clear the cache" find a paragraph titled "Invalidating entries".

Configuration: ``EMBEDDING_MODEL`` plus ``EMBEDDING_BASE_URL`` /
``EMBEDDING_API_KEY``, which default to the chat provider's values. With
Ollama use model ``nomic-embed-text`` and base URL ``http://localhost:11434/v1``.
"""
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx

from app.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

BATCH_SIZE = 64


class EmbeddingClient:
    """Compute embeddings in batches with a bounded timeout."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.model = model or settings.embedding_model
        self.base_url = (base_url or settings.embedding_base_url or settings.openai_base_url).rstrip("/")
        self.api_key = api_key or settings.embedding_api_key or settings.openai_api_key
        self.timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return one vector per input text, in order."""
        return (await self.embed_with_usage(texts)).vectors

    async def embed_with_usage(self, texts: List[str]) -> "EmbeddingResult":
        """Vectors plus the tokens the provider billed and the time it took.

        Some OpenAI-compatible endpoints (Gemini's among them) return no
        ``usage`` block for embeddings. Then the token count is estimated
        from the text length (about four characters per token) and flagged
        as an estimate, so the cost is still attributed rather than lost.
        """
        started = time.perf_counter()
        vectors, tokens, reported = await self._embed(texts)
        estimated = not reported and bool(texts)
        if estimated:
            tokens = sum(estimate_tokens(text) for text in texts)
        return EmbeddingResult(
            vectors=vectors,
            tokens=tokens,
            tokens_estimated=estimated,
            latency_ms=(time.perf_counter() - started) * 1000,
            model=self.model,
            estimated_cost_usd=round(tokens * settings.embedding_price_for(self.model) / 1_000_000, 10),
        )

    async def _embed(self, texts: List[str]) -> tuple[List[List[float]], int, bool]:
        """(vectors, tokens, whether the provider reported the tokens)."""
        if not texts:
            return [], 0, True
        if not self.api_key:
            raise ExternalServiceError(
                "Embeddings",
                "Embedding provider is not configured (set OPENAI_API_KEY or EMBEDDING_API_KEY)",
                details={"reason": "missing_api_key"},
            )

        vectors: List[List[float]] = []
        tokens = 0
        reported = False
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            for start in range(0, len(texts), BATCH_SIZE):
                batch = texts[start : start + BATCH_SIZE]
                try:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json={"model": self.model, "input": batch},
                    )
                except httpx.TimeoutException as exc:
                    raise ExternalServiceError(
                        "Embeddings", "Embedding request timed out", details={"reason": "timeout"}
                    ) from exc
                except httpx.HTTPError as exc:
                    raise ExternalServiceError(
                        "Embeddings", "Embedding request failed", details={"reason": "network_error"}
                    ) from exc

                if response.status_code >= 400:
                    logger.warning(
                        "Embedding provider returned %s", response.status_code,
                        extra={"status_code": response.status_code},
                    )
                    raise ExternalServiceError(
                        "Embeddings",
                        "Embedding provider returned an error",
                        details={"reason": f"http_{response.status_code}", "status_code": response.status_code},
                    )

                payload = response.json()
                usage = payload.get("usage") if isinstance(payload, dict) else None
                if isinstance(usage, dict) and (usage.get("prompt_tokens") or usage.get("total_tokens")):
                    tokens += int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0)
                    reported = True
                items = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(items, list) or len(items) != len(batch):
                    raise ExternalServiceError(
                        "Embeddings", "Embedding provider returned an invalid response",
                        details={"reason": "invalid_response"},
                    )
                # The API may return items out of order; sort by index.
                items = sorted(items, key=lambda item: item.get("index", 0))
                for item in items:
                    vector = item.get("embedding")
                    if not isinstance(vector, list) or not vector:
                        raise ExternalServiceError(
                            "Embeddings", "Embedding provider returned an empty vector",
                            details={"reason": "invalid_response"},
                        )
                    vectors.append([float(v) for v in vector])
        return vectors, tokens, reported


CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token count for providers that do not report embedding usage."""
    return max(1, round(len(text) / CHARS_PER_TOKEN))


@dataclass
class EmbeddingResult:
    vectors: List[List[float]]
    #: Tokens the provider reported, or an estimate when it reports none (see tokens_estimated).
    tokens: int
    latency_ms: float
    model: str
    #: From EMBEDDING_PRICING_TABLE / EMBEDDING_PRICE_PER_MILLION: an estimate, not billing.
    estimated_cost_usd: float
    tokens_estimated: bool = False


def get_embedding_client() -> EmbeddingClient:
    """Factory the RAG services use; tests replace it with a fake."""
    return EmbeddingClient()
