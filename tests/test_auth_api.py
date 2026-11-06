"""
End-to-end authentication, token, and role-based access control tests.
"""
from app.core.security import JWTHandler

REGISTER_PAYLOAD = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "password123",
    "role": "viewer",
}

RULE_PAYLOAD = {
    "endpoint_pattern": "/api/v1/rbac-test",
    "ttl": 300,
    "enabled": True,
    "cache_by_user": False,
    "cache_by_query_params": False,
    "cache_by_headers": False,
    "max_cache_size": 1000,
    "priority": 1,
    "description": "rbac test rule",
}


async def test_register_creates_user(client):
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["role"] == "viewer"
    assert body["is_active"] is True
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflict(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 409


async def test_register_cannot_escalate_role(client):
    payload = {
        **REGISTER_PAYLOAD,
        "username": "mallory",
        "email": "mallory@example.com",
        "role": "admin",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 200
    assert res.json()["role"] == "viewer"


async def test_login_success_returns_typed_tokens(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    access = JWTHandler.decode_token(body["access_token"])
    assert access["type"] == "access"
    assert access["role"] == "viewer"

    refresh = JWTHandler.decode_token(body["refresh_token"])
    assert refresh["type"] == "refresh"


async def test_login_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    assert res.status_code == 401


async def test_login_unknown_user_rejected(client):
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "whatever123"},
    )
    assert res.status_code == 401


async def test_access_token_allowed_on_protected_endpoint(client, admin_headers):
    res = await client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert res.status_code == 200
    assert "total_requests" in res.json()


async def test_missing_auth_header_rejected(client):
    res = await client.get("/api/v1/analytics/summary")
    assert res.status_code == 401


async def test_refresh_token_rejected_on_protected_endpoint(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-pass-123"},
    )
    refresh_token = login.json()["refresh_token"]
    res = await client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert res.status_code == 401


async def test_refresh_endpoint_exchanges_refresh_token(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-pass-123"},
    )
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert JWTHandler.decode_token(body["access_token"])["type"] == "access"


async def test_refresh_endpoint_rejects_access_token(client, admin_headers):
    access_token = admin_headers["Authorization"].split(" ")[1]
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert res.status_code == 401


async def test_viewer_cannot_create_rule(client, viewer_headers):
    res = await client.post("/api/v1/rules", json=RULE_PAYLOAD, headers=viewer_headers)
    assert res.status_code == 403


async def test_unauthenticated_rule_create_rejected(client):
    res = await client.post("/api/v1/rules", json=RULE_PAYLOAD)
    assert res.status_code == 401


async def test_operator_can_create_and_update_rule(client, operator_headers):
    created = await client.post("/api/v1/rules", json=RULE_PAYLOAD, headers=operator_headers)
    assert created.status_code == 200
    rule_id = created.json()["id"]

    updated = await client.put(
        f"/api/v1/rules/{rule_id}", json={"ttl": 600}, headers=operator_headers
    )
    assert updated.status_code == 200
    assert updated.json()["ttl"] == 600


async def test_operator_cannot_delete_rule(client, operator_headers):
    created = await client.post("/api/v1/rules", json=RULE_PAYLOAD, headers=operator_headers)
    rule_id = created.json()["id"]
    res = await client.delete(f"/api/v1/rules/{rule_id}", headers=operator_headers)
    assert res.status_code == 403


async def test_admin_can_delete_rule(client, admin_headers):
    created = await client.post("/api/v1/rules", json=RULE_PAYLOAD, headers=admin_headers)
    rule_id = created.json()["id"]
    res = await client.delete(f"/api/v1/rules/{rule_id}", headers=admin_headers)
    assert res.status_code == 200
