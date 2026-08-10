"""
Demo endpoints used for live demonstrations and load testing.

`/api/v1/demo/latency` simulates a slow upstream call (e.g. a 150ms database
query or third-party API) so the caching layer has real work to absorb. It is
deliberately excluded from auth and rate limiting — it exists purely to make
"cache ON vs OFF" benchmarks meaningful.
"""
import asyncio
import logging

from fastapi import APIRouter

router = APIRouter(prefix="/demo", tags=["Demo"])
logger = logging.getLogger(__name__)

SIMULATED_LATENCY_SECONDS = 0.15


@router.get("/latency")
async def simulated_latency():
    """Simulate a slow upstream call, then return a small JSON payload."""
    await asyncio.sleep(SIMULATED_LATENCY_SECONDS)
    return {
        "status": "ok",
        "source": "backend",
        "work_ms": SIMULATED_LATENCY_SECONDS * 1000,
        "items": list(range(1, 51)),
    }
