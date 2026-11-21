"""Request telemetry: inbound requests and outbound Optimizer calls are
buffered and shipped to the Optimizer's ingest endpoint, failing open."""
import json

import httpx
import pytest

from esone_api import optimizer, telemetry
from esone_api.config import get_settings
from tests.conftest import bearer, login, register

ANSWER = {"question": "q", "answer": "a", "answered_by": "crawler", "cached": False, "sources": []}
CACHED_ANSWER = {**ANSWER, "answered_by": "cache", "cached": True}


class FakeOptimizer:
    """Optimizer stand-in: login, answers, and the ingest endpoint."""

    def __init__(self):
        self.ingested: list[dict] = []
        self.ingest_status = 202
        self.logins = 0
        self.answer: dict = ANSWER

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            self.logins += 1
            return httpx.Response(200, json={"access_token": f"tok-{self.logins}", "refresh_token": "r", "expires_in": 900})
        if request.url.path == "/api/v1/answers":
            return httpx.Response(200, json=self.answer)
        if request.url.path == telemetry.INGEST_PATH:
            assert request.headers.get("authorization", "").startswith("Bearer tok-")
            body = json.loads(request.content)
            if self.ingest_status == 202:
                self.ingested.extend(body["records"])
                return httpx.Response(202, json={"accepted": len(body["records"])})
            return httpx.Response(self.ingest_status, json={"detail": "nope"})
        return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
async def wired(client, monkeypatch):
    fake = FakeOptimizer()
    monkeypatch.setenv("ESONE_OPTIMIZER_URL", "http://optimizer.test")
    monkeypatch.setenv("ESONE_OPTIMIZER_USERNAME", "esone-bot")
    monkeypatch.setenv("ESONE_OPTIMIZER_PASSWORD", "bot-pass-123")
    monkeypatch.setenv("ESONE_TELEMETRY_FLUSH_SECONDS", "3600")  # never flushes on its own in tests
    get_settings.cache_clear()
    await optimizer.reset_optimizer()
    optimizer._transport_factory = lambda: httpx.MockTransport(fake.handler)
    telemetry.buffer.clear()
    yield client, fake
    optimizer._transport_factory = None
    await optimizer.reset_optimizer()
    telemetry.buffer.clear()
    get_settings.cache_clear()


def _rows(direction: str) -> list[dict]:
    return [r for r in list(telemetry.buffer._records) if r["direction"] == direction]


async def test_inbound_requests_are_recorded_with_a_correlation_id(wired):
    client, _ = wired
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    correlation = res.headers["X-Correlation-ID"]
    assert len(correlation) == 32

    rows = _rows("inbound")
    assert [r["endpoint"] for r in rows] == ["/api/v1/health"]
    row = rows[0]
    assert row["service"] == "esone" and row["method"] == "GET" and row["status_code"] == 200
    assert row["correlation_id"] == correlation and row["response_time_ms"] >= 0
    assert "occurred_at" in row

    # A caller-supplied correlation id is honoured, and errors are recorded too.
    res = await client.get("/api/v1/users/me", headers={"X-Correlation-ID": "trace-abc"})
    assert res.status_code == 401
    assert _rows("inbound")[-1]["correlation_id"] == "trace-abc"
    assert _rows("inbound")[-1]["status_code"] == 401


async def test_outbound_optimizer_calls_share_the_inbound_correlation_id(wired):
    client, _ = wired
    await register(client)
    headers = bearer(await login(client))
    telemetry.buffer.clear()

    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 200, res.text
    correlation = res.headers["X-Correlation-ID"]

    outbound = _rows("outbound")
    assert [r["endpoint"] for r in outbound] == [
        "optimizer.test/api/v1/auth/login",
        "optimizer.test/api/v1/answers",
    ]
    for row in outbound:
        assert row["upstream_host"] == "optimizer.test"
        assert row["correlation_id"] == correlation
        assert row["status_code"] == 200
    chat_row = _rows("inbound")[-1]
    assert chat_row["endpoint"] == "/api/v1/chat"
    assert chat_row["cache_hit"] is False  # crawled answer


async def test_cached_answers_are_marked_as_cache_hits(wired):
    client, fake = wired
    await register(client)
    headers = bearer(await login(client))
    fake.answer = CACHED_ANSWER
    telemetry.buffer.clear()

    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 200 and res.json()["cached"] is True
    assert _rows("inbound")[-1]["cache_hit"] is True
    # The flag is per request: the next, uncached request starts clean.
    fake.answer = ANSWER
    await client.post("/api/v1/chat", json={"question": "What is Rust?"}, headers=headers)
    assert _rows("inbound")[-1]["cache_hit"] is False


async def test_shipper_posts_batches_and_requeues_on_transient_failure(wired):
    client, fake = wired
    await client.get("/api/v1/health")
    await client.get("/api/v1/health")
    assert len(telemetry.buffer) == 2

    shipper = telemetry.TelemetryShipper(
        base_url="http://optimizer.test",
        token_provider=optimizer.get_optimizer().service_token,
        on_unauthorized=optimizer.get_optimizer().forget_token,
        flush_seconds=3600,
        transport=httpx.MockTransport(fake.handler),
    )
    try:
        assert await shipper.flush() == 2
        assert [r["endpoint"] for r in fake.ingested] == ["/api/v1/health", "/api/v1/health"]
        assert fake.ingested[0]["service"] == "esone"
        # Signing in to ship is itself an outbound call, recorded for the next batch.
        assert [r["endpoint"] for r in telemetry.buffer._records] == ["optimizer.test/api/v1/auth/login"]
        telemetry.buffer.clear()

        # A 429 keeps the batch for the next tick instead of losing it.
        fake.ingest_status = 429
        await client.get("/api/v1/health")
        assert await shipper.flush() == 0
        assert len(telemetry.buffer) == 1
        fake.ingest_status = 202
        assert await shipper.flush() == 1
        assert shipper.shipped == 3
    finally:
        await shipper.stop()


async def test_proxied_requests_are_not_recorded_twice(wired):
    """Through the Optimizer proxy, the proxy logs the request; Esone only adds
    the outbound calls and tells the proxy about cache hits via a header."""
    client, fake = wired
    await register(client)
    headers = {**bearer(await login(client)), "X-Proxied-By": "api-optimizer", "X-Correlation-ID": "via-proxy-1"}
    fake.answer = CACHED_ANSWER
    telemetry.buffer.clear()

    res = await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    assert res.status_code == 200
    assert res.headers["X-Cache-Hit"] == "true"
    assert res.headers["X-Correlation-ID"] == "via-proxy-1"
    assert _rows("inbound") == []
    outbound = _rows("outbound")  # service login + the answers call, both tied to the proxy's id
    assert [r["endpoint"] for r in outbound] == ["optimizer.test/api/v1/auth/login", "optimizer.test/api/v1/answers"]
    assert {r["correlation_id"] for r in outbound} == {"via-proxy-1"}


async def test_telemetry_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("ESONE_TELEMETRY_ENABLED", "false")
    get_settings.cache_clear()
    telemetry.buffer.clear()
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert "X-Correlation-ID" not in res.headers
    assert len(telemetry.buffer) == 0
    get_settings.cache_clear()


async def test_rate_limited_logins_are_recorded(wired, monkeypatch):
    """The limiter sits inside telemetry, so its 429s reach the Optimizer's dashboard."""
    client, _ = wired
    monkeypatch.setenv("ESONE_AUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    body = {"username": "nobody", "password": "wrong-pass-123"}
    statuses = [(await client.post("/api/v1/auth/login", json=body)).status_code for _ in range(3)]
    assert statuses == [401, 401, 429]
    rows = [r for r in _rows("inbound") if r["endpoint"] == "/api/v1/auth/login"]
    assert [r["status_code"] for r in rows] == [401, 401, 429]


async def test_rate_limited_response_carries_cors_headers(wired, monkeypatch):
    """CORS is outermost: a browser can read the 429 instead of seeing a network error."""
    client, _ = wired
    monkeypatch.setenv("ESONE_AUTH_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("ESONE_CORS_ORIGINS", "http://localhost:4000")
    get_settings.cache_clear()
    body = {"username": "nobody", "password": "wrong-pass-123"}
    origin = {"Origin": "http://localhost:4000"}
    assert (await client.post("/api/v1/auth/login", json=body, headers=origin)).status_code == 401
    blocked = await client.post("/api/v1/auth/login", json=body, headers=origin)
    assert blocked.status_code == 429
    assert blocked.headers.get("access-control-allow-origin") == "http://localhost:4000"


async def test_rows_carry_the_signed_in_user_and_nothing_personal(wired):
    client, _ = wired
    await register(client)
    tokens = await login(client)
    headers = bearer(tokens)
    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    telemetry.buffer.clear()

    await client.post("/api/v1/chat", json={"question": "What is Python?"}, headers=headers)
    await client.get("/api/v1/health")
    ref = f"esone:{me['id']}"
    chat_in = [r for r in _rows("inbound") if r["endpoint"] == "/api/v1/chat"]
    assert [r["end_user"] for r in chat_in] == [ref]
    assert {r["end_user"] for r in _rows("outbound")} == {ref}  # calls made for that request
    assert _rows("inbound")[-1]["end_user"] is None  # anonymous request
    for row in telemetry.buffer._records:
        assert "alice" not in json.dumps(row)  # never the username or email


async def test_a_successful_login_is_attributed_to_that_user(wired):
    client, _ = wired
    await register(client)
    telemetry.buffer.clear()
    await login(client)
    await client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong-password-1"})
    ok, failed = [r for r in _rows("inbound") if r["endpoint"] == "/api/v1/auth/login"]
    assert ok["status_code"] == 200 and ok["end_user"] and ok["end_user"].startswith("esone:")
    assert failed["status_code"] == 401 and failed["end_user"] is None
