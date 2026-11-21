from app.config import settings
from app.database.db import async_session_maker
from app.models import AnswerLog

PRICING_PATH = "/api/v1/pricing"


async def test_pricing_requires_auth(client):
    res = await client.get(PRICING_PATH)
    assert res.status_code == 401


async def test_pricing_exposes_configured_tables(client, viewer_headers):
    res = await client.get(PRICING_PATH, headers=viewer_headers)
    assert res.status_code == 200
    body = res.json()

    assert body["currency"] == settings.pricing_currency
    assert body["effective_date"] == settings.pricing_effective_date
    assert body["unit"] == "per 1,000,000 tokens"
    assert body["source"] == "PRICING_TABLE / EMBEDDING_PRICING_TABLE"
    assert body["is_estimate"] is True
    assert "billing" in body["note"].lower()

    assert body["defaults"]["chat_prompt_per_million"] == settings.chat_prompt_price_per_million
    assert body["defaults"]["chat_completion_per_million"] == settings.chat_completion_price_per_million
    assert body["defaults"]["embedding_per_million"] == settings.embedding_price_per_million

    assert body["billing"]["currency"] == "INR"
    assert body["billing"]["rate_per_token"] == settings.answers_inr_per_token
    assert body["billing"]["unit"] == "per non-cached token"
    assert "cache" in body["billing"]["note"].lower()

    chat_models = body["chat_models"]
    assert [item["model"] for item in chat_models] == sorted(item["model"] for item in chat_models)
    by_model = {item["model"]: item for item in chat_models}
    expected = settings.PRICING_TABLE["gpt-4o-mini"]
    assert by_model["gpt-4o-mini"]["prompt_per_million"] == expected["prompt"]
    assert by_model["gpt-4o-mini"]["completion_per_million"] == expected["completion"]

    embedding_models = body["embedding_models"]
    assert [item["model"] for item in embedding_models] == sorted(item["model"] for item in embedding_models)
    embeddings = {item["model"]: item for item in embedding_models}
    assert embeddings["gemini-embedding-001"]["price_per_million"] == settings.EMBEDDING_PRICING_TABLE["gemini-embedding-001"]


async def _old_test_pricing_users_requires_admin(client, viewer_headers, operator_headers):
    assert (await client.get(f"{PRICING_PATH}/users")).status_code == 401
    assert (await client.get(f"{PRICING_PATH}/users", headers=viewer_headers)).status_code == 403
    assert (await client.get(f"{PRICING_PATH}/users", headers=operator_headers)).status_code == 403


async def test_pricing_users_breaks_down_billable_tokens(client, admin_headers):
    async with async_session_maker() as session:
        session.add_all(
            [
                AnswerLog(
                    user_id=2,
                    question="What is Python?",
                    question_hash="a" * 40,
                    answer="A language.",
                    answered_by="model",
                    cache_status="miss",
                    status="ok",
                    total_tokens=10,
                    billable_tokens=10,
                    cost_inr=50.0,
                ),
                AnswerLog(
                    user_id=2,
                    end_user="esone:42",
                    question="What is Python?",
                    question_hash="a" * 40,
                    answer="A language.",
                    answered_by="cache",
                    cache_status="exact_hit",
                    status="ok",
                    total_tokens=0,
                    billable_tokens=0,
                    cost_inr=0.0,
                ),
                AnswerLog(
                    user_id=3,
                    question="What is Python?",
                    question_hash="a" * 40,
                    answer="A language.",
                    answered_by="crawler",
                    cache_status="bypassed",
                    status="ok",
                    total_tokens=4,
                    billable_tokens=4,
                    cost_inr=20.0,
                ),
            ]
        )
        await session.commit()

    res = await client.get(f"{PRICING_PATH}/users", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["currency"] == "INR"
    assert body["rate_per_token"] == settings.answers_inr_per_token
    assert body["total_billable_tokens"] == 14
    assert body["total_cost_inr"] == 70.0

    items = {(item["user_id"], item["end_user"]): item for item in body["items"]}
    assert items[(2, None)]["username"] == "operator"
    assert items[(2, None)]["billable_tokens"] == 10
    assert items[(2, None)]["cost_inr"] == 50.0
    assert items[(2, "esone:42")]["cached_answers"] == 1
    assert items[(2, "esone:42")]["billable_tokens"] == 0
    assert items[(3, None)]["uncached_answers"] == 1
    assert items[(3, None)]["cost_inr"] == 20.0
    assert items[(1, None)]["answers"] == 0



async def test_pricing_users_is_scoped_to_the_caller(client, viewer_headers, admin_headers):
    """Every user sees only their own billing; admins see everyone."""
    from sqlalchemy import text

    from app.database.db import async_session_maker

    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM answer_logs"))
        for uid, tokens in ((2, 100), (3, 40)):
            await session.execute(text(
                "INSERT INTO answer_logs (user_id, question, question_hash, answer, answered_by, found, sources, "
                "status, cache_status, total_tokens, billable_tokens, cost_inr, created_at, updated_at) VALUES "
                f"({uid}, 'q', 'h{uid}', 'a', 'model', 1, '[]', 'ok', 'miss', {tokens}, {tokens}, {tokens * 5.0}, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
        await session.commit()

    own = (await client.get("/api/v1/pricing/users", headers=viewer_headers)).json()
    assert own["scope"] == "own"
    assert {item["user_id"] for item in own["items"]} == {3}
    assert own["total_billable_tokens"] == 40 and own["total_cost_inr"] == 200.0

    res = await client.get("/api/v1/pricing/users", headers=admin_headers)
    everyone = res.json()
    assert everyone["scope"] == "all" and everyone["total_cost_inr"] == 700.0
