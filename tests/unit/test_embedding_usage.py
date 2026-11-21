"""Embedding usage: reported tokens are used as is; missing usage is estimated and flagged."""
import httpx
import pytest

from app.ai.rag.embeddings import EmbeddingClient, estimate_tokens
from app.config import settings


def _transport(with_usage: bool):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"object": "list", "model": "test-embed", "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}]}
        if with_usage:
            body["usage"] = {"prompt_tokens": 7, "total_tokens": 7}
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_reported_usage_is_used(monkeypatch):
    monkeypatch.setattr(settings, "embedding_price_per_million", 10.0)
    client = EmbeddingClient(model="test-embed", base_url="http://embed.test", api_key="k", transport=_transport(True))
    result = await client.embed_with_usage(["Who painted the Mona Lisa?"])
    assert result.tokens == 7 and result.tokens_estimated is False
    assert result.estimated_cost_usd == pytest.approx(7 * 10.0 / 1_000_000)
    assert result.vectors == [[0.1, 0.2]] and result.model == "test-embed"


@pytest.mark.asyncio
async def test_missing_usage_is_estimated_and_flagged(monkeypatch):
    monkeypatch.setattr(settings, "embedding_price_per_million", 10.0)
    client = EmbeddingClient(model="test-embed", base_url="http://embed.test", api_key="k", transport=_transport(False))
    text = "Who painted the Mona Lisa?"
    result = await client.embed_with_usage([text])
    assert result.tokens_estimated is True
    assert result.tokens == estimate_tokens(text) == round(len(text) / 4)
    assert result.estimated_cost_usd == pytest.approx(result.tokens * 10.0 / 1_000_000)


def test_table_price_beats_the_global_default(monkeypatch):
    monkeypatch.setattr(settings, "embedding_price_per_million", 1.0)
    assert settings.embedding_price_for("gemini-embedding-001") == settings.EMBEDDING_PRICING_TABLE["gemini-embedding-001"]
    assert settings.embedding_price_for("unknown-model") == 1.0
