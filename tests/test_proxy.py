"""
/proxy/<service>/<path>: a monitored service's API behind the gateway.

The upstream is played by an httpx.MockTransport; the gateway's own
middleware (metrics, rate limit, cache) runs for real.
"""
import json

import httpx
import pytest
from sqlalchemy import delete, select

from app.api.v1 import proxy as proxy_module
from app.config import settings
from app.database.db import async_session_maker
from app.models import APILog


class FakeEsone:
    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.fail = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.fail:
            raise httpx.ConnectError("down")
        if request.url.path == "/api/v1/chat":
            return httpx.Response(
                200,
                json={"answer": "cached answer", "cached": True},
                headers={"X-Cache-Hit": "true", "X-Correlation-ID": request.headers.get("x-correlation-id", "")},
            )
        if request.url.path == "/api/v1/users/me":
            if request.headers.get("authorization") != "Bearer esone-token":
                return httpx.Response(401, json={"detail": "Not authenticated"})
            return httpx.Response(200, json={"username": "alice"})
        return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
async def esone(monkeypatch):
    fake = FakeEsone()
    monkeypatch.setattr(settings, "proxy_upstreams", {"esone": "http://esone.test"})
    await proxy_module.close_proxy_client()
    proxy_module._transport_factory = lambda: httpx.MockTransport(fake.handler)
    async with async_session_maker() as session:
        await session.execute(delete(APILog).where(APILog.service == "esone"))
        await session.commit()
    yield fake
    proxy_module._transport_factory = None
    await proxy_module.close_proxy_client()


async def _esone_rows() -> list[APILog]:
    async with async_session_maker() as session:
        rows = await session.execute(select(APILog).where(APILog.service == "esone").order_by(APILog.id))
        return list(rows.scalars().all())


async def test_forwards_request_and_records_it_under_the_service(client, esone):
    res = await client.post(
        "/proxy/esone/api/v1/chat?lang=en",
        json={"question": "What is Python?"},
        headers={"Authorization": "Bearer esone-token", "X-Custom": "kept"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["answer"] == "cached answer"

    # No gateway token was needed: the upstream authenticates its own users.
    sent = esone.calls[-1]
    assert sent.method == "POST" and sent.url.path == "/api/v1/chat" and sent.url.query == b"lang=en"
    assert json.loads(sent.content) == {"question": "What is Python?"}
    assert sent.headers["authorization"] == "Bearer esone-token"
    assert sent.headers["x-custom"] == "kept"
    assert sent.headers["x-proxied-by"] == "api-optimizer"
    assert sent.headers["x-forwarded-for"]  # the real client address reaches the upstream
    assert sent.headers["x-correlation-id"] == res.headers["X-Correlation-ID"]

    rows = await _esone_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row.service == "esone" and row.direction == "inbound"
    assert row.endpoint == "/proxy/esone/api/v1/chat" and row.status_code == 200
    assert row.cache_hit is True  # from the upstream's X-Cache-Hit header
    assert row.user_id is None


async def test_upstream_errors_are_passed_through_or_mapped(client, esone):
    res = await client.get("/proxy/esone/api/v1/users/me")
    assert res.status_code == 401  # the upstream's own answer
    res = await client.get("/proxy/esone/api/v1/users/me", headers={"Authorization": "Bearer esone-token"})
    assert res.status_code == 200 and res.json() == {"username": "alice"}

    esone.fail = True
    res = await client.get("/proxy/esone/api/v1/users/me")
    assert res.status_code == 502
    assert res.json()["error_code"] == "UPSTREAM_UNAVAILABLE"

    res = await client.get("/proxy/nobody/api/v1/health")
    assert res.status_code == 404

    statuses = [row.status_code for row in await _esone_rows()]
    assert statuses == [401, 200, 502]


async def test_proxied_responses_are_not_cached_by_gateway_rules(client, esone, admin_headers):
    """A substring rule for /api/v1/users must not apply to /proxy/esone/api/v1/users/me,
    and a credentialed proxied GET is never cached without a header-keyed rule."""
    created = await client.post(
        "/api/v1/rules",
        json={"endpoint_pattern": "/api/v1/users", "ttl": 60, "enabled": True, "priority": 100},
        headers=admin_headers,
    )
    assert created.status_code in (200, 201), created.text
    try:
        for _ in range(2):
            res = await client.get("/proxy/esone/api/v1/users/me", headers={"Authorization": "Bearer esone-token"})
            assert res.status_code == 200
            assert res.headers.get("X-Cache-Hit") is None
        assert len([c for c in esone.calls if c.url.path == "/api/v1/users/me"]) == 2  # both reached the upstream
    finally:
        await client.delete(f"/api/v1/rules/{created.json()['id']}", headers=admin_headers)
