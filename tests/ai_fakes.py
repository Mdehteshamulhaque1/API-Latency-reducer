"""
Deterministic fakes for the AI tests: no network, no model downloads.

* ``FakeEmbeddingClient`` turns text into a hashed bag-of-words vector, so
  cosine similarity is meaningful (shared words -> closer vectors).
* ``fake_chat_service`` returns a scripted answer and records the prompt
  it received, so tests can assert what reached the "model".
"""
import hashlib
import json
import math
import re
from types import SimpleNamespace
from typing import List

import httpx

from app.services.chat import ChatService
from app.services.circuit_breaker import CircuitBreaker

DIMENSIONS = 128
_WORD = re.compile(r"[a-z0-9]+")


class FakeEmbeddingClient:
    model = "fake-bow-embedding"
    configured = True
    #: USD per million tokens the fake charges, so cost arithmetic can be asserted.
    price_per_million = 100.0

    async def embed_with_usage(self, texts: List[str]):
        from app.ai.rag.embeddings import EmbeddingResult

        vectors = await self.embed(texts)
        tokens = sum(len(_WORD.findall(text)) for text in texts)
        return EmbeddingResult(
            vectors=vectors, tokens=tokens, latency_ms=1.0, model=self.model,
            estimated_cost_usd=round(tokens * self.price_per_million / 1_000_000, 10),
        )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * DIMENSIONS
            for word in _WORD.findall(text.lower()):
                if len(word) < 3:
                    continue
                slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMENSIONS
                vector[slot] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectors.append([v / norm for v in vector])
        return vectors


class NoopCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        return True


def fake_chat_service(answer: str, seen: dict):
    """Build a ChatService whose provider echoes ``answer`` and records prompts."""

    def handler(request):
        body = json.loads(request.content)
        seen["messages"] = body["messages"]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-fake",
                "created": 1,
                "model": "fake-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52},
            },
        )

    settings_obj = SimpleNamespace(
        openai_api_key="test-key",
        openai_base_url="https://api.openai.com/v1",
        openai_model="fake-model",
        openai_primary_model=None,
        openai_fallback_model=None,
        openai_timeout_seconds=10.0,
        openai_max_retries=0,
        redis_cache_ttl=3600,
    )
    return ChatService(
        settings_obj,
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
        breaker=CircuitBreaker(name="fake", failure_threshold=100, cooldown_seconds=30),
    )


def failing_chat_service():
    def handler(request):
        return httpx.Response(503, json={"error": "down"})

    settings_obj = SimpleNamespace(
        openai_api_key="test-key",
        openai_base_url="https://api.openai.com/v1",
        openai_model="fake-model",
        openai_primary_model=None,
        openai_fallback_model=None,
        openai_timeout_seconds=10.0,
        openai_max_retries=0,
        redis_cache_ttl=3600,
    )
    return ChatService(
        settings_obj,
        transport=httpx.MockTransport(handler),
        cache=NoopCache(),
        breaker=CircuitBreaker(name="fake-fail", failure_threshold=100, cooldown_seconds=30),
    )


def patch_ai(monkeypatch, *, answer: str = "ok", fail_llm: bool = False) -> dict:
    """Route every AI module to the fakes. Returns the dict that records prompts."""
    seen: dict = {}
    import app.ai.rag.ingest as ingest_mod
    import app.ai.rag.retrieval as retrieval_mod
    import app.ai.rag.answer as answer_mod
    import app.ai.assistant.engine as engine_mod
    import app.ai.assistant.recommendations as rec_mod
    import app.ai.assistant.troubleshoot as ts_mod

    monkeypatch.setattr(ingest_mod, "get_embedding_client", lambda: FakeEmbeddingClient())
    monkeypatch.setattr(retrieval_mod, "get_embedding_client", lambda: FakeEmbeddingClient())
    factory = (lambda: failing_chat_service()) if fail_llm else (lambda: fake_chat_service(answer, seen))
    for module in (answer_mod, engine_mod, rec_mod, ts_mod):
        monkeypatch.setattr(module, "get_chat_service", factory)
    return seen
