"""
Input screen applied before any text reaches the model.

    messages ──► injection scan ──► PII masking ──► ScreenResult
                     │                  │
                     │                  └─ masked copy of the messages + counts
                     └─ highest severity; "high" blocks when blocking is on

The screen never raises. The caller decides what to do with ``blocked``
(the chat route returns HTTP 400) and persists ``events`` in a background
task so the audit trail never slows the response.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.ai.guardrails.events import (
    CATEGORY_INJECTION_BLOCKED,
    CATEGORY_INJECTION_DETECTED,
    CATEGORY_PII_MASKED,
)
from app.ai.guardrails.injection import scan_texts
from app.ai.guardrails.pii import mask_text
from app.config import settings
from app.schemas.chat import ChatMessage


@dataclass
class ScreenResult:
    messages: List[ChatMessage]
    blocked: bool = False
    block_reason: Optional[str] = None
    injection_severity: str = "none"
    injection_rules: List[str] = field(default_factory=list)
    pii_counts: dict = field(default_factory=dict)
    events: List[dict] = field(default_factory=list)


def screen_messages(
    messages: List[ChatMessage],
    *,
    feature: str,
    user_id: Optional[int],
    correlation_id: Optional[str],
    block_injection: Optional[bool] = None,
    mask_pii: Optional[bool] = None,
) -> ScreenResult:
    """Scan caller-supplied messages for injection and mask PII."""
    block_injection = settings.guardrails_block_injection if block_injection is None else block_injection
    mask_pii = settings.guardrails_mask_pii if mask_pii is None else mask_pii

    base = {"feature": feature, "user_id": user_id, "correlation_id": correlation_id}
    result = ScreenResult(messages=list(messages))

    # 1. Injection: anything the caller wrote (user or system role) is untrusted.
    scan = scan_texts([m.content for m in messages if m.role != "assistant"])
    result.injection_severity = scan.severity
    result.injection_rules = scan.matched
    if scan.detected:
        detail = ",".join(scan.matched)[:255]
        if scan.severity == "high" and block_injection:
            result.blocked = True
            result.block_reason = "Request blocked by the prompt-injection guardrail"
            result.events.append(
                {**base, "category": CATEGORY_INJECTION_BLOCKED, "severity": "high",
                 "detail": detail, "blocked": True}
            )
            return result
        result.events.append(
            {**base, "category": CATEGORY_INJECTION_DETECTED, "severity": scan.severity,
             "detail": detail, "blocked": False}
        )

    # 2. PII: mask before the text leaves the service.
    if mask_pii:
        masked_messages: List[ChatMessage] = []
        counts: dict = {}
        for message in messages:
            if message.role == "assistant":
                masked_messages.append(message)
                continue
            outcome = mask_text(message.content)
            for key, value in outcome.counts.items():
                counts[key] = counts.get(key, 0) + value
            masked_messages.append(
                message.model_copy(update={"content": outcome.text}) if outcome.masked else message
            )
        result.messages = masked_messages
        result.pii_counts = counts
        if counts:
            result.events.append(
                {**base, "category": CATEGORY_PII_MASKED, "severity": "low",
                 "detail": " ".join(f"{k}={v}" for k, v in sorted(counts.items())),
                 "blocked": False}
            )

    return result
