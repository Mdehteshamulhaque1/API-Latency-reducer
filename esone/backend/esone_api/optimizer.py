"""Client for the API Optimizer's LLM gateway, used by the chat proxy.

Esone users never talk to the Optimizer directly. This client signs in to the
Optimizer with one service account (ESONE_OPTIMIZER_USERNAME / PASSWORD),
keeps the access token in memory, re-authenticates once on 401, and forwards
chat messages. Only short status codes are logged, never message bodies.
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import HTTPException, status

from esone_api.config import get_settings
from esone_api.telemetry import outbound_hooks

logger = logging.getLogger(__name__)

UNAVAILABLE = "The assistant is unavailable right now. Please try again in a moment"
NOT_CONFIGURED = "The assistant is not configured on this server"


def _safe_detail(res: httpx.Response) -> str | None:
    """A short, user-safe message from an Optimizer error body, if it has one."""
    try:
        detail = res.json().get("detail")
    except (ValueError, AttributeError):
        return None
    if isinstance(detail, str) and detail.strip():
        return detail.strip()[:200]
    return None


class OptimizerClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Every call through this client is recorded as outbound telemetry.
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, transport=transport, event_hooks=outbound_hooks()
        )
        self.transport = transport
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _login(self) -> None:
        try:
            res = await self._client.post(
                "/api/v1/auth/login",
                json={"username": self._username, "password": self._password},
            )
        except httpx.HTTPError as exc:
            logger.warning("optimizer login failed: %s", type(exc).__name__)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=UNAVAILABLE) from exc
        if res.status_code != 200:
            logger.warning("optimizer login rejected: status=%s", res.status_code)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE)
        token = res.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE)
        self._access_token = token

    async def _ensure_token(self) -> str:
        if self._access_token is None:
            async with self._lock:
                if self._access_token is None:
                    await self._login()
        assert self._access_token is not None
        return self._access_token

    async def service_token(self) -> str:
        """The service account's access token (signing in when needed); used by telemetry."""
        return await self._ensure_token()

    def forget_token(self) -> None:
        """Drop the cached token so the next call signs in again."""
        self._access_token = None

    async def ask(
        self, question: str, *, user_ref: str | None = None, user_name: str | None = None, user_email: str | None = None
    ) -> dict:
        """Forward a question to the answers pipeline; return its AnswerResponse as a dict.

        ``user_ref`` is an opaque end-user reference (``esone:<id>``) so the
        Optimizer keeps a record per Esone user while its cache stays shared.
        """
        body: dict = {"question": question}
        if user_ref:
            body["user_ref"] = user_ref
            # Lets the Optimizer's admin user directory show who the reference is.
            if user_name:
                body["user_name"] = user_name
            if user_email:
                body["user_email"] = user_email
        return await self._post("/api/v1/answers", body, required="answer")

    async def chat(self, body: dict) -> dict:
        """Forward a ChatRequest body to the raw LLM gateway (kept for tooling)."""
        return await self._post("/api/v1/chat", body, required="content")

    async def _post(self, path: str, body: dict, *, required: str) -> dict:
        res: httpx.Response | None = None
        for attempt in (1, 2):
            token = await self._ensure_token()
            try:
                res = await self._client.post(path, json=body, headers={"Authorization": f"Bearer {token}"})
            except httpx.HTTPError as exc:
                logger.warning("optimizer chat request failed: %s", type(exc).__name__)
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=UNAVAILABLE) from exc
            if res.status_code == 401 and attempt == 1:
                # Service token expired or was revoked: sign in again, once.
                self._access_token = None
                continue
            break

        assert res is not None
        if res.status_code == 200:
            data = res.json()
            if not isinstance(data, dict) or not isinstance(data.get(required), str):
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=UNAVAILABLE)
            return data

        detail = _safe_detail(res)
        if res.status_code in (400, 422):
            # Guardrail block or validation error: the message is meant for the user.
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail or "The question was rejected")
        if res.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Please wait a moment")
        logger.warning("optimizer request failed: path=%s status=%s", path, res.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=detail or UNAVAILABLE)


_client: OptimizerClient | None = None
_transport_factory = None  # tests inject an httpx.MockTransport here


def get_optimizer() -> OptimizerClient | None:
    """The process-wide client, or None when the Optimizer is not configured."""
    global _client
    if _client is None:
        s = get_settings()
        if not (s.optimizer_url and s.optimizer_username and s.optimizer_password):
            return None
        _client = OptimizerClient(
            s.optimizer_url,
            s.optimizer_username,
            s.optimizer_password,
            s.optimizer_timeout_seconds,
            transport=_transport_factory() if _transport_factory else None,
        )
    return _client


async def reset_optimizer() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
