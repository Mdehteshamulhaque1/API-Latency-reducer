"""Tiny OpenAI‑compatible local server for Phase‑5 evaluation.

- Configurable latency (mean +/- jitter)
- Fixed token usage
- Failure‑injection mode (X% timeouts / 5xx / 429)
- Deterministic (no external calls)
"""

from __future__ import annotations

import os
import random
import time
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

# ----------------------------------------------------------------------
# Configuration (all environment‑variables, defaults shown)
# ----------------------------------------------------------------------
LATENCY_MEAN = float(os.getenv("MOCK_LATENCY_MEAN", "1.5"))          # seconds
LATENCY_JITTER = float(os.getenv("MOCK_LATENCY_JITTER", "0.3"))    # +/- seconds
FAILURE_RATE = float(os.getenv("MOCK_FAILURE_RATE", "0.0"))         # 0‑100 %
FAILURE_TYPE = os.getenv("MOCK_FAILURE_TYPE", "none")               # "timeout","5xx","429","none"
# Fixed token usage
PROMPT_TOKENS = int(os.getenv("MOCK_PROMPT_TOKENS", "20"))
COMPLETION_TOKENS = int(os.getenv("MOCK_COMPLETION_TOKENS", "50"))

# ----------------------------------------------------------------------
# Helper: generate a latency sample from a uniform distribution
# ----------------------------------------------------------------------
def _sample_latency() -> float:
    lo = max(0.0, LATENCY_MEAN - LATENCY_JITTER)
    hi = LATENCY_MEAN + LATENCY_JITTER
    return random.uniform(lo, hi)


# ----------------------------------------------------------------------
# Helper: decide whether this request fails and what kind
# ----------------------------------------------------------------------
def _should_fail() -> bool:
    return random.random() < (FAILURE_RATE / 100.0)


def _failure_type() -> str | None:
    if FAILURE_TYPE == "timeout":
        return "timeout"
    if FAILURE_TYPE == "5xx":
        return "5xx"
    if FAILURE_TYPE == "429":
        return "429"
    return None


# ----------------------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------------------
app = FastAPI(title="Mock OpenAI Chat")


@app.post("/v1/chat/completions")
async def chat_completion(request: Request):
    body = await request.json()
    model = body.get("model", "gpt-3.5-turbo")

    if _should_fail():
        ftype = _failure_type()
        if ftype == "timeout":
            raise HTTPException(status_code=500, detail="Timeout")
        if ftype == "5xx":
            raise HTTPException(status_code=500, detail="Server error")
        if ftype == "429":
            raise HTTPException(status_code=429, detail="Rate limited")

    latency = _sample_latency()
    await asyncio.sleep(latency)
    return JSONResponse(
        {
            "id": f"chatcmpl-{random.randint(1000, 9999)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": f"Mock reply ({latency:.2f}s)"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": PROMPT_TOKENS,
                "completion_tokens": COMPLETION_TOKENS,
                "total_tokens": PROMPT_TOKENS + COMPLETION_TOKENS,
            },
        },
        status_code=200,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("MOCK_PORT", "8001")))