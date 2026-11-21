"""Request telemetry: ship every request Esone serves, and every call it makes,
to the API Optimizer so its dashboard can analyse Esone's traffic.

Two sources feed one in-memory buffer:

* ``RequestTelemetryMiddleware`` times each inbound HTTP request (method,
  path, status, latency, client IP, sizes) and attaches a correlation id.
* ``outbound_hooks()`` are httpx event hooks for the Optimizer client, so
  each call Esone makes is recorded as an "outbound" row carrying the same
  correlation id as the inbound request that triggered it.

``TelemetryShipper`` drains the buffer every ``ESONE_TELEMETRY_FLUSH_SECONDS``
and POSTs a batch to ``{ESONE_OPTIMIZER_URL}/api/v1/ingest/requests`` with
the service account's token. Everything fails open: the buffer is bounded,
shipping errors are logged as status codes only, and no request or response
body ever leaves this process.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from esone_api.config import get_settings
from esone_api.ratelimit import client_ip

logger = logging.getLogger(__name__)

INGEST_PATH = "/api/v1/ingest/requests"
# Requests arriving through the Optimizer's reverse proxy carry this header.
# The proxy already records them, so only outbound calls are reported here
# for those, and the cache outcome is handed back in a response header.
PROXIED_BY_HEADER = "x-proxied-by"
MAX_BATCH = 500
SKIPPED_PATHS = {"/docs", "/openapi.json", "/favicon.ico"}

# Correlation id of the inbound request being handled on this task, so the
# outbound calls it makes can be tied back to it.
current_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("esone_correlation_id", default="")
# Per-request flags a route can set (the chat proxy marks answers the
# Optimizer served from its semantic cache). The middleware runs the route in
# a child task, where ContextVar assignments are invisible to the parent, so
# the middleware installs a dict and the route mutates it in place.
_request_flags: contextvars.ContextVar[dict | None] = contextvars.ContextVar("esone_request_flags", default=None)


def mark_cache_hit(hit: bool = True) -> None:
    """Flag the request being handled as served from a cache."""
    flags = _request_flags.get()
    if flags is not None:
        flags["cache_hit"] = bool(hit)


def end_user_ref(user_id: int) -> str:
    """Opaque reference for an Esone account, shared with the Optimizer ("esone:7")."""
    return f"esone:{user_id}"


def mark_end_user(user_id: int) -> None:
    """Attribute the request being handled (and the calls it makes) to a signed-in user.

    Only the opaque reference is shipped, never a name or email, so the
    Optimizer's dashboard can show that person's own API activity.
    """
    flags = _request_flags.get()
    if flags is not None:
        flags["end_user"] = end_user_ref(user_id)


def _current_end_user() -> str | None:
    flags = _request_flags.get()
    return flags.get("end_user") if flags else None


def _content_length(headers: Any) -> int:
    raw = headers.get("content-length")
    try:
        return max(0, int(raw)) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


class TelemetryBuffer:
    """Bounded FIFO of request records awaiting shipment (oldest dropped first)."""

    def __init__(self, max_size: int = 5000) -> None:
        self._records: deque[dict] = deque(maxlen=max_size)
        self.dropped = 0

    def __len__(self) -> int:
        return len(self._records)

    def add(self, record: dict) -> None:
        if len(self._records) == self._records.maxlen:
            self.dropped += 1
        self._records.append(record)

    def drain(self, limit: int = MAX_BATCH) -> list[dict]:
        batch = []
        while self._records and len(batch) < limit:
            batch.append(self._records.popleft())
        return batch

    def requeue(self, records: list[dict]) -> None:
        """Put a failed batch back at the front, newest-first so order is kept."""
        for record in reversed(records):
            self._records.appendleft(record)

    def clear(self) -> None:
        self._records.clear()


buffer = TelemetryBuffer()


def _service_name() -> str:
    return get_settings().telemetry_service_name


def record_inbound(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    ip: str,
    correlation_id: str,
    request_bytes: int = 0,
    response_bytes: int = 0,
    query: str | None = None,
    cache_hit: bool = False,
    end_user: str | None = None,
) -> None:
    buffer.add(
        {
            "service": _service_name(),
            "direction": "inbound",
            "end_user": end_user,
            "method": method,
            "endpoint": path,
            "path": path,
            "status_code": status_code,
            "response_time_ms": round(duration_ms, 3),
            "client_ip": ip[:45],
            "correlation_id": correlation_id[:36],
            "cache_hit": cache_hit,
            "request_size_bytes": request_bytes,
            "response_size_bytes": response_bytes,
            "query_params": query[:2000] if query else None,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
    )


def record_outbound(
    *,
    method: str,
    host: str,
    path: str,
    status_code: int,
    duration_ms: float,
    correlation_id: str,
    request_bytes: int = 0,
    response_bytes: int = 0,
    error: str | None = None,
    end_user: str | None = None,
) -> None:
    buffer.add(
        {
            "service": _service_name(),
            "direction": "outbound",
            "end_user": end_user,
            "method": method,
            # Host + path so an outbound call never merges with an inbound
            # route of the same path in the dashboard's endpoint tables.
            "endpoint": f"{host}{path}"[:500],
            "path": path[:500],
            "upstream_host": host[:255],
            "status_code": status_code,
            "response_time_ms": round(duration_ms, 3),
            "client_ip": _service_name()[:45],
            "correlation_id": correlation_id[:36],
            "request_size_bytes": request_bytes,
            "response_size_bytes": response_bytes,
            "error_message": error[:500] if error else None,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
    )


class RequestTelemetryMiddleware(BaseHTTPMiddleware):
    """Record every inbound request and expose its correlation id."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in SKIPPED_PATHS or not get_settings().telemetry_enabled:
            return await call_next(request)

        correlation_id = (request.headers.get("x-correlation-id") or uuid.uuid4().hex)[:36]
        token = current_correlation_id.set(correlation_id)
        flags: dict = {"cache_hit": False}
        flags_token = _request_flags.set(flags)
        started = time.perf_counter()
        status_code = 500
        response = None
        proxied = bool(request.headers.get(PROXIED_BY_HEADER))
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = correlation_id
            if flags.get("cache_hit"):
                response.headers["X-Cache-Hit"] = "true"  # read by the Optimizer's proxy
            return response
        finally:
            current_correlation_id.reset(token)
            _request_flags.reset(flags_token)
            if not proxied:  # the proxy logged this request already
                try:
                    record_inbound(
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        ip=client_ip(request),
                        correlation_id=correlation_id,
                        request_bytes=_content_length(request.headers),
                        response_bytes=_content_length(response.headers) if response is not None else 0,
                        query=str(request.query_params) if request.query_params else None,
                        cache_hit=bool(flags.get("cache_hit")),
                        end_user=flags.get("end_user"),
                    )
                except Exception as exc:  # noqa: BLE001  telemetry must never break a request
                    logger.debug("telemetry record skipped: %s", type(exc).__name__)


# ---------------------------------------------------------------- outbound ---

_STARTED_KEY = "esone_telemetry_started"


async def _on_request(request: httpx.Request) -> None:
    request.extensions[_STARTED_KEY] = time.perf_counter()


async def _on_response(response: httpx.Response) -> None:
    request = response.request
    started = request.extensions.get(_STARTED_KEY)
    if started is None or request.url.path == INGEST_PATH:
        return
    try:
        record_outbound(
            method=request.method,
            host=request.url.netloc.decode(),
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=(time.perf_counter() - started) * 1000,
            correlation_id=current_correlation_id.get(),
            request_bytes=_content_length(request.headers),
            response_bytes=_content_length(response.headers),
            end_user=_current_end_user(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("outbound telemetry skipped: %s", type(exc).__name__)


def outbound_hooks() -> dict[str, list[Callable]]:
    """httpx ``event_hooks`` that record each call made through a client."""
    return {"request": [_on_request], "response": [_on_response]}


# ----------------------------------------------------------------- shipper ---


class TelemetryShipper:
    """Background task that POSTs buffered records to the Optimizer."""

    def __init__(
        self,
        base_url: str,
        token_provider: Callable[[], Any],
        on_unauthorized: Callable[[], None],
        flush_seconds: float,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)
        self._token_provider = token_provider  # async callable -> bearer token
        self._on_unauthorized = on_unauthorized  # drop the cached token
        self._flush_seconds = max(1.0, flush_seconds)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.shipped = 0

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="esone-telemetry")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=self._flush_seconds + 5)
            except (TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            self._task = None
        await self._client.aclose()

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._flush_seconds)
                except TimeoutError:
                    pass
                await self.flush()
        except asyncio.CancelledError:  # shutdown: one last attempt, then leave
            pass

    async def flush(self) -> int:
        """Ship up to one batch. Returns the number of records accepted."""
        batch = buffer.drain()
        if not batch:
            return 0
        try:
            token = await self._token_provider()
        except Exception as exc:  # noqa: BLE001  (HTTPException from login, network errors)
            logger.warning("telemetry: could not obtain optimizer token (%s); keeping %d records", type(exc).__name__, len(batch))
            buffer.requeue(batch)
            return 0
        try:
            res = await self._client.post(
                INGEST_PATH, json={"records": batch}, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.HTTPError as exc:
            logger.warning("telemetry: ship failed (%s); keeping %d records", type(exc).__name__, len(batch))
            buffer.requeue(batch)
            return 0
        if res.status_code == 202:
            self.shipped += len(batch)
            if buffer.dropped:
                logger.warning("telemetry: buffer overflowed, %d records were dropped", buffer.dropped)
                buffer.dropped = 0
            return len(batch)
        if res.status_code == 401:
            self._on_unauthorized()  # next flush signs in again
            buffer.requeue(batch)
        elif res.status_code == 429 or res.status_code >= 500:
            buffer.requeue(batch)  # transient: retry next tick
        # 4xx other than the above: the batch is malformed for this server; drop it.
        logger.warning("telemetry: optimizer rejected batch status=%s (%d records)", res.status_code, len(batch))
        return 0


_shipper: TelemetryShipper | None = None


async def start_shipper() -> None:
    """Create and start the shipper when telemetry and the Optimizer are configured."""
    global _shipper
    from esone_api.optimizer import get_optimizer  # late import: optimizer imports telemetry hooks

    settings = get_settings()
    client = get_optimizer()
    if not settings.telemetry_enabled or client is None:
        return
    _shipper = TelemetryShipper(
        base_url=settings.optimizer_url or "",
        token_provider=client.service_token,
        on_unauthorized=client.forget_token,
        flush_seconds=settings.telemetry_flush_seconds,
        timeout=settings.optimizer_timeout_seconds,
        transport=client.transport,
    )
    _shipper.start()
    logger.info("telemetry: shipping request logs to the optimizer every %.0fs", settings.telemetry_flush_seconds)


async def stop_shipper() -> None:
    global _shipper
    if _shipper is not None:
        await _shipper.flush()
        await _shipper.stop()
        _shipper = None
