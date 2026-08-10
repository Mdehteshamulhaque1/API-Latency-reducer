"""
Cache middleware for response caching using Redis cache rules.
"""
import fnmatch
import json
import logging
from typing import Optional

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.constants import CACHE_KEY_RULE_PREFIX, CACHE_KEY_RULES_LIST, CACHE_RULES_LIST_TTL
from app.models import CacheRule
from app.services.cache import CacheService
from app.utils.redis_client import redis_client
from app.database.db import async_session_maker

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Cache middleware that applies cache rules before endpoint execution.
    """

    EXCLUDED_PATHS = {
        "/",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/api/v1/ping",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    CACHEABLE_METHODS = {"GET"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS or request.method not in self.CACHEABLE_METHODS:
            request.state.cache_hit = False
            request.state.cache_key = None
            return await call_next(request)

        cache_rule = await self._find_cache_rule(request.url.path)
        if cache_rule is None or not cache_rule.enabled:
            request.state.cache_hit = False
            request.state.cache_key = None
            return await call_next(request)

        cache_key = self._build_cache_key(cache_rule, request)
        request.state.cache_key = cache_key

        cache_service = CacheService(redis_client)
        cached = await cache_service.get(cache_key)
        if cached and isinstance(cached, dict):
            request.state.cache_hit = True
            logger.info("Cache hit for %s", cache_key)
            return self._build_response(cached)

        request.state.cache_hit = False
        response = await call_next(request)

        # BaseHTTPMiddleware returns a streaming response; consume its body so
        # it can be stored in Redis, then rebuild a replayable response object
        # (Starlette >=1.x: Response.body no longer exists for these responses).
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        original_background = getattr(response, "background", None)

        response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        if original_background is not None:
            response.background = original_background

        await self._cache_response(cache_rule, request, response, cache_service, cache_key, body_bytes)
        return response

    @staticmethod
    def _pattern_matches(pattern: str, path: str) -> bool:
        """Match a cache-rule pattern against a request path.

        Patterns containing glob characters (*, ?, []) are matched with
        fnmatch; otherwise a substring match is used (backwards compatible).
        """
        if any(char in pattern for char in "*?["):
            return fnmatch.fnmatchcase(path, pattern)
        return pattern in path

    async def _get_enabled_rules(self) -> list:
        """Load enabled cache rules, caching the list in Redis for a few seconds.

        Reading rules from Redis instead of the database on every request keeps
        the database out of the request hot path; the short TTL bounds how long
        a rule change takes to propagate, and rule writes invalidate it eagerly.
        """
        client = redis_client.client
        if client is not None:
            try:
                raw = await client.get(CACHE_KEY_RULES_LIST)
                if raw:
                    return [CacheRule(**item) for item in json.loads(raw)]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read cached rules list: %s", exc)

        async with async_session_maker() as session:
            result = await session.execute(
                select(CacheRule).where(CacheRule.enabled == True)  # noqa: E712
            )
            rules = result.scalars().all()

        if client is not None:
            try:
                payload = [
                    {
                        "endpoint_pattern": rule.endpoint_pattern,
                        "ttl": rule.ttl,
                        "enabled": rule.enabled,
                        "cache_by_user": rule.cache_by_user,
                        "cache_by_query_params": rule.cache_by_query_params,
                        "cache_by_headers": rule.cache_by_headers,
                        "max_cache_size": rule.max_cache_size,
                        "priority": rule.priority,
                        "description": rule.description,
                    }
                    for rule in rules
                ]
                await client.set(
                    CACHE_KEY_RULES_LIST,
                    json.dumps(payload),
                    ex=CACHE_RULES_LIST_TTL,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to cache rules list: %s", exc)

        return rules

    async def _find_cache_rule(self, path: str) -> Optional[CacheRule]:
        rules = await self._get_enabled_rules()

        for rule in sorted(rules, key=lambda item: item.priority, reverse=True):
            if rule.endpoint_pattern and self._pattern_matches(rule.endpoint_pattern, path):
                return rule
        return None

    def _build_cache_key(self, rule: CacheRule, request: Request) -> str:
        cache_service = CacheService(redis_client)
        user_id = getattr(request.state, "user_id", None)
        # Authenticated requests are always scoped per user so a cached
        # response for one user can never be served to another, regardless of
        # the rule's `cache_by_user` flag. Only anonymous requests share cache
        # entries across clients.
        cache_by_user = True if user_id is not None else rule.cache_by_user
        query_params = dict(request.query_params) if rule.cache_by_query_params else None
        headers = dict(request.headers) if rule.cache_by_headers else None
        base_key = cache_service._generate_cache_key(
            endpoint=request.url.path,
            cache_by_user=cache_by_user,
            cache_by_params=rule.cache_by_query_params,
            cache_by_headers=rule.cache_by_headers,
            user_id=user_id,
            query_params=query_params,
            headers=headers,
        )
        return f"{CACHE_KEY_RULE_PREFIX}{rule.endpoint_pattern}:{base_key}"

    def _build_response(self, cached: dict) -> Response:
        body = cached.get("body", "")
        status_code = int(cached.get("status_code", 200))
        headers = cached.get("headers", {}) or {}
        media_type = headers.get("content-type", "application/json")

        response = Response(content=body, status_code=status_code, media_type=media_type)
        for name, value in headers.items():
            name_lower = name.lower()
            if name_lower in {"content-length", "content-encoding"}:
                continue
            response.headers[name] = value

        response.headers["X-Cache-Hit"] = "true"
        return response

    async def _cache_response(
        self,
        rule: CacheRule,
        request: Request,
        response: Response,
        cache_service: CacheService,
        cache_key: str,
        body_bytes: bytes,
    ) -> None:
        if response.status_code != 200:
            return

        try:
            body_content = body_bytes.decode("utf-8")
        except Exception:
            body_content = str(body_bytes)

        ttl = rule.ttl if rule.ttl and rule.ttl > 0 else None
        headers = {
            name: value
            for name, value in response.headers.items()
            if name.lower() in {"content-type", "cache-control", "etag"}
        }
        cache_value = {
            "status_code": response.status_code,
            "headers": headers,
            "body": body_content,
        }

        await cache_service.set(cache_key, cache_value, ttl=ttl)
        response.headers["X-Cache-Stored"] = "true"
