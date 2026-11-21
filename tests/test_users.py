"""Admin user directory: list every user, and everything about one of them."""
import asyncio

import httpx

from app.ai.answers.crawler import Crawler
from app.ai.answers.semantic_cache import SemanticCache
from app.config import settings
from app.services.answers import AnswerService
from tests.ai_fakes import FakeEmbeddingClient
from tests.test_answers import FakeKnowledge, FakeWikipedia, reset_rate_limits


def _service(knowledge):
    wiki = FakeWikipedia()
    return AnswerService(
        cache=SemanticCache(threshold=0.5),
        crawler=Crawler(transport=httpx.MockTransport(wiki.handler), max_results=2),
        embedding_factory=FakeEmbeddingClient,
        knowledge_fn=knowledge,
        model_first=True,
    )


async def test_directory_is_admin_only(client, viewer_headers, operator_headers):
    for headers in (viewer_headers, operator_headers):
        assert (await client.get("/api/v1/users", headers=headers)).status_code == 403
        assert (await client.get("/api/v1/users/detail", params={"key": "account:1"}, headers=headers)).status_code == 403
    assert (await client.get("/api/v1/users")).status_code == 401


async def test_lists_accounts_and_end_users_with_their_activity(client, admin_headers, operator_headers, viewer_headers, monkeypatch):
    knowledge = FakeKnowledge("Python is a programming language.")
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", lambda: _service(knowledge))

    # The viewer asks for themself; the operator account forwards two questions for an end user.
    await client.post("/api/v1/answers", json={"question": "What is the Python programming language?"}, headers=viewer_headers)
    for _ in range(2):
        res = await client.post(
            "/api/v1/answers",
            json={"question": "What is the Python programming language?", "user_ref": "esone:7",
                  "user_name": "priya", "user_email": "priya@example.com"},
            headers=operator_headers,
        )
        assert res.status_code == 200, res.text
    await asyncio.sleep(0.3)  # background writes
    await reset_rate_limits()

    page = (await client.get("/api/v1/users", headers=admin_headers)).json()
    by_key = {item["key"]: item for item in page["items"]}
    viewer = by_key["account:3"]
    assert viewer["kind"] == "account" and viewer["username"] == "viewer" and viewer["role"] == "viewer"
    assert viewer["searches"] == 1 and viewer["billable_tokens"] == 30
    assert viewer["cost_inr"] == round(30 * settings.answers_inr_per_token, 2)
    priya = by_key["esone:7"]
    assert priya["kind"] == "end_user" and priya["service"] == "esone"
    assert priya["username"] == "priya" and priya["email"] == "priya@example.com"
    assert priya["searches"] == 2 and priya["cache_hits"] == 2  # the viewer's answer was already cached
    assert priya["cost_inr"] == 0.0

    # Search and kind filters.
    found = (await client.get("/api/v1/users", params={"search": "priya"}, headers=admin_headers)).json()
    assert [item["key"] for item in found["items"]] == ["esone:7"]
    accounts = (await client.get("/api/v1/users", params={"kind": "account"}, headers=admin_headers)).json()
    assert {item["kind"] for item in accounts["items"]} == {"account"}
    assert {"account:1", "account:2", "account:3"} <= {item["key"] for item in accounts["items"]}


async def test_account_detail_has_every_section(client, admin_headers, viewer_headers, monkeypatch):
    knowledge = FakeKnowledge("Python is a programming language.")
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", lambda: _service(knowledge))
    await client.post("/api/v1/answers", json={"question": "What is the Python programming language?"}, headers=viewer_headers)
    await client.get("/api/v1/rate-limits/me", headers=viewer_headers)
    await asyncio.sleep(0.3)
    await reset_rate_limits()

    res = await client.get("/api/v1/users/detail", params={"key": "account:3"}, headers=admin_headers)
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["profile"]["username"] == "viewer" and d["profile"]["role"] == "viewer" and d["notes"] == []
    assert d["traffic"]["total_requests"] >= 2  # the gateway logged this account's own requests
    assert d["rate_limit"]["identifier"] == "user:3" and d["rate_limit"]["tier"] == "user"
    assert d["answers"]["questions"] == 1 and d["answers"]["scope"] == "user"
    assert d["recent_answers"][0]["question"] == "What is the Python programming language?"
    assert d["billing"]["billable_tokens"] == 30 and d["billing"]["paid_answers"] == 1
    assert d["ai_usage"]["scope"] == "user" and d["guardrails"]["scope"] == "user"

    missing = await client.get("/api/v1/users/detail", params={"key": "account:999"}, headers=admin_headers)
    assert missing.status_code == 404


async def test_end_user_detail_explains_what_is_not_available(client, admin_headers, operator_headers, monkeypatch):
    knowledge = FakeKnowledge("Python is a programming language.")
    monkeypatch.setattr("app.api.v1.answers.get_answer_service", lambda: _service(knowledge))
    await client.post(
        "/api/v1/answers",
        json={"question": "What is the Python programming language?", "user_ref": "esone:9", "user_name": "ravi"},
        headers=operator_headers,
    )
    await asyncio.sleep(0.3)
    await reset_rate_limits()

    d = (await client.get("/api/v1/users/detail", params={"key": "esone:9"}, headers=admin_headers)).json()
    assert d["profile"]["kind"] == "end_user" and d["profile"]["username"] == "ravi" and d["profile"]["service"] == "esone"
    assert d["answers"]["questions"] == 1 and d["billing"]["billable_tokens"] == 30
    assert d["traffic"]["total_requests"] == 0 and d["ai_usage"] is None and d["guardrails"] is None
    assert "service account" in d["notes"][0]

    # The operator that forwarded it is flagged as a service account.
    op = (await client.get("/api/v1/users/detail", params={"key": "account:2"}, headers=admin_headers)).json()
    assert op["notes"] and "service account" in op["notes"][0]
    assert (await client.get("/api/v1/users/detail", params={"key": "esone:404"}, headers=admin_headers)).status_code == 404
