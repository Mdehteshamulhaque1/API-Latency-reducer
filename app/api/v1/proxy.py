"""
Reverse proxy: put a monitored service's whole API behind this gateway.

``/proxy/{service}/{path}`` forwards the request to the upstream configured
for ``service`` in ``PROXY_UPSTREAMS`` (for example ``esone`` ->
``http://localhost:8000``) and returns its response unchanged. Because the
request passes through this app's middleware, every call is recorded in
``api_logs`` under that service (so the dashboard shows the service's real
traffic as it happens), rate limited per client, and cached when a rule for
``/proxy/<service>/...`` says so.

The gateway does not authenticate these requests itself: the upstream owns
its users and checks their tokens. The client's address is passed on in
``X-Forwarded-For`` so the upstream's own limits keep working, the request's
correlation id is forwarded, and an upstream ``X-Cache-Hit: true`` header
(Esone sets it when an answer came from the semantic cache) is recorded as a
cache hit on the row.
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Proxy"])

PROXY_PREFIX = "/proxy/"
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

# Hop-by-hop headers and ones the proxy sets itself are not forwarded.
_SKIP_REQUEST_HEADERS = {
    "host", "content-length", "connection", "keep-alive", "transfer-encoding",
    "te", "trailer", "upgrade", "proxy-authorization", "proxy-connection",
    "accept-encoding",  # ask the upstream for an identity body so it can be re-sent as is
}
_SKIP_RESPONSE_HEADERS = {
    "content-length", "content-encoding", "connection", "keep-alive",
    "transfer-encoding", "te", "trailer", "upgrade", "server", "date",
}

_client: Optional[httpx.AsyncClient] = None
_transport_factory = None  # tests inject an httpx.MockTransport here


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.proxy_timeout_seconds),
            transport=_transport_factory() if _transport_factory else None,
            follow_redirects=False,
        )
    return _client


async def close_proxy_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def upstream_for(service: str) -> Optional[str]:
    """Base URL configured for a service name, without a trailing slash."""
    base = settings.proxy_upstreams.get(service)
    return base.rstrip("/") if base else None


@router.api_route(PROXY_PREFIX + "{service}/{path:path}", methods=METHODS, include_in_schema=False)
async def proxy(service: str, path: str, request: Request) -> Response:
    base = upstream_for(service)
    if base is None:
        return JSONResponse(status_code=404, content={"detail": "Unknown proxied service", "error_code": "NOT_FOUND"})

    # Attribute the api_logs row to the proxied service (read by MetricsMiddleware).
    request.state.service = service

    url = f"{base}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _SKIP_REQUEST_HEADERS}
    client_ip = request.client.host if request.client is not None else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    headers["X-Forwarded-For"] = f"{forwarded_for}, {client_ip}" if forwarded_for else client_ip
    headers["X-Forwarded-Proto"] = request.url.scheme
    headers["X-Forwarded-Host"] = request.headers.get("host", "")
    headers["X-Proxied-By"] = "api-optimizer"
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        headers["X-Correlation-ID"] = str(correlation_id)

    try:
        body = await request.body()
    except ClientDisconnect:
        # The browser cancelled the request (a page navigation, an aborted
        # fetch); nothing to forward. Nginx's 499 is the conventional status.
        logger.info("proxy %s: client disconnected before the request was read (%s %s)", service, request.method, path)
        return Response(status_code=499)
    try:
        upstream = await _get_client().request(request.method, url, headers=headers, content=body)
    except httpx.TimeoutException:
        logger.warning("proxy %s: upstream timed out (%s %s)", service, request.method, path)
        return JSONResponse(status_code=504, content={"detail": "Upstream service timed out", "error_code": "UPSTREAM_TIMEOUT"})
    except httpx.HTTPError as exc:
        logger.warning("proxy %s: upstream unreachable (%s)", service, type(exc).__name__)
        return JSONResponse(status_code=502, content={"detail": "Upstream service unavailable", "error_code": "UPSTREAM_UNAVAILABLE"})

    if upstream.headers.get("x-cache-hit", "").lower() == "true":
        request.state.cache_hit = True

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESPONSE_HEADERS}
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
