"""
Background task helpers for analytics and benchmark reporting.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


REPORT_DIRECTORY = Path("logs") / "benchmark_reports"
REPORT_FILE = REPORT_DIRECTORY / "latest.json"


def persist_benchmark_report(report: Mapping[str, Any]) -> None:
    """Persist the latest benchmark report to disk for later review."""
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": dict(report),
    }

    REPORT_FILE.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("Benchmark report persisted to %s", REPORT_FILE)


def warm_cache_snapshot(keys: list[str]) -> None:
    """Log a cache warming snapshot for operational visibility."""
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    snapshot_file = REPORT_DIRECTORY / "cache_warmup.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "keys": keys,
    }
    snapshot_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Cache warmup snapshot persisted to %s", snapshot_file)
