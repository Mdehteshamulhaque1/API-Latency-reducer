"""
Demo endpoints used for live demonstrations and load testing.

`/api/v1/demo/latency` simulates a slow upstream call (e.g. a 150ms database
query or third-party API) so the caching layer has real work to absorb. It is
deliberately excluded from auth and rate limiting — it exists purely to make
"cache ON vs OFF" benchmarks meaningful. It is disabled by default and must be
explicitly enabled via DEMO_ENDPOINT_ENABLED=True.
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/demo", tags=["Demo"])
logger = logging.getLogger(__name__)

SIMULATED_LATENCY_SECONDS = 0.15


@router.get("/latency")
async def simulated_latency():
    """Simulate a slow upstream call, then return a small JSON payload."""
    if not settings.demo_endpoint_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    await asyncio.sleep(SIMULATED_LATENCY_SECONDS)
    return {
        "status": "ok",
        "source": "backend",
        "work_ms": SIMULATED_LATENCY_SECONDS * 1000,
        "items": list(range(1, 51)),
    }
