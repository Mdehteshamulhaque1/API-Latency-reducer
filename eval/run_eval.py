#!/usr/bin/env python3
"""Complete rewrite of eval/run_eval.py with all fixes."""

import os
import sys
import json
import csv
import re
import time
import datetime
import httpx
import pathlib
import subprocess
import subprocess as sp

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EVAL_DIR = PROJECT_ROOT / "eval"
DOCS_DIR = PROJECT_ROOT / "docs"
STATS_CSV = EVAL_DIR / "locust_output_stats.csv"
MOCK_SERVER_PORT = 8001
GATEWAY_PORT = 8000
GATEWAY_URL = f"http://127.0.0.1:{GATEWAY_PORT}/metrics"


def _env_float(name, default=0.0):
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name, default=0):
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_str(name, default=""):
    val = os.getenv(name)
    return val if val is not None else default


def wait_for_server(host="127.0.0.1", port=GATEWAY_PORT, timeout=30):
    """Poll until the gateway /metrics endpoint responds.

    Retries every 1 second for up *timeout* seconds.
    Raises RuntimeError if the server never responds.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{GATEWAY_URL}", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(
        f"Gateway at {GATEWAY_URL} did not become ready within {timeout}s"
    )


def start_mock_server():
    """Start the mock OpenAI-compatible server on port 8001."""
    env = os.environ.copy()
    env["MOCK_LATENCY_MEAN"] = "1.0"
    env["MOCK_LATENCY_JITTER"] = "0.2"
    env["MOCK_FAILURE_RATE"] = "0"
    env["MOCK_FAILURE_TYPE"] = "none"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "eval.mock_openai:app",
         "--host", "0.0.0.0", "--port", str(MOCK_SERVER_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def stop_mock_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def start_gateway():
    """Start the FastAPI gateway on port 8000 with high rate limits."""
    env = os.environ.copy()
    env["MOCK_LATENCY_MEAN"] = "1.0"
    env["MOCK_LATENCY_JITTER"] = "0.2"
    env["MOCK_FAILURE_RATE"] = "0"
    env["MOCK_FAILURE_TYPE"] = "none"
    env["RATE_LIMIT_DEFAULT_REQUESTS"] = "10000"
    env["RATE_LIMIT_DEFAULT_PERIOD"] = "3600"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", str(GATEWAY_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def stop_gateway(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def flush_redis():
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host="localhost", port=6379, db=15)
        r.flushdb()
    except Exception:
        pass


def discard_warmup(seconds=5):
    pass


def read_metrics_snapshot():
    """Read /metrics snapshot and return relevant counters."""
    try:
        r = httpx.get(GATEWAY_URL, timeout=3)
        if r.status_code != 200:
            return None
        body = r.text
        import re
        hits_m = re.search(r'cache:stats:hits\s*(\d+)', body)
        misses_m = re.search(r'cache:stats:misses\s*(\d+)', body)
        fallback_success_m = re.search(
            r'chat_fallback_total\{status="success"\}\s*(\d+)', body)
        fallback_error_m = re.search(
            r'chat_fallback_total\{status="error"\}\s*(\d+)', body)
        cost_m = re.search(r'chat_estimated_cost_usd_total\s*(\d+\.?\d*)', body)
        return {
            "cache_hits": int(hits_m.group(1)) if hits_m else 0,
            "cache_misses": int(misses_m.group(1)) if misses_m else 0,
            "fallback_success": int(fallback_success_m.group(1))
            if fallback_success_m else 0,
            "fallback_error": int(fallback_error_m.group(1)) if fallback_error_m else 0,
            "estimated_cost": float(cost_m.group(1)) if cost_m else 0.0,
        }
    except Exception:
        return None


def run_locust_csv(*, users, spawn_rate, run_time, csv_path,
                   env_extra=None, cwd=None):
    env = os.environ.copy()
    env.update(env_extra or {})

    # Clean any stale CSV files
    for p in [csv_path, csv_path.parent / (csv_path.stem + "_stats_history.csv")]:
        if p.is_file():
            p.unlink()

    discard_warmup(5)

    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(EVAL_DIR / "locustfile.py"),
        "--headless",
        "--csv", str(csv_path),
        "--host", "http://127.0.0.1:8001",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
    stats = {
        "median_latency": None,
        "p95_latency": None,
        "p99_latency": None,
        "rps": None,
        "total_requests": None,
        "total_failures": None,
        "cache_hit_rate": None,
        "estimated_cost_per_1k": None,
    }

    # Check for the actual stats CSV that Locust creates
    stats_csv = csv_path.parent / (csv_path.stem + "_stats.csv")
    if not stats_csv.is_file():
        msg = ("WARNING: " + str(stats_csv)
               + " not found – Locust CSV not generated.\n"
               "stderr: " + (proc.stderr[-300:]
                            if len(proc.stderr) > 300 else proc.stderr))
        raise RuntimeError(msg)

    with open(stats_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 3:
        raise RuntimeError("WARNING: CSV has fewer than 3 rows.")

    header = rows[0]
    data_rows = rows[1:]

    # Find the aggregated row
    aggregated_row = None
    for row in reversed(data_rows):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) > 1 and row[1].strip().lower() == "aggregated":
            aggregated_row = row
            break
        try:
            _ = int(row[2].strip())
            aggregated_row = row
            break
        except Exception:
            continue

    if aggregated_row is None:
        for row in reversed(data_rows):
            if len(row) > 2 and row[2].strip().isdigit():
                aggregated_row = row
                break

    if aggregated_row is None:
        raise RuntimeError("WARNING: could not identify the aggregated row.")

    # Build a name→position map from the header
    col_map = {}
    for i, name in enumerate(header):
        if name not in col_map:
            col_map[name] = i

    def col(name, default=None):
        pos = col_map.get(name)
        if pos is None or pos >= len(aggregated_row):
            return default
        v = aggregated_row[pos].strip()
        if not v:
            return default
        return v

    try:
        total_requests = int(col("Request Count") or 0)
    except Exception:
        total_requests = None
    try:
        total_failures = int(col("Failure Count") or 0)
    except Exception:
        total_failures = None

    median_ms = None
    try:
        median_ms = float(col("Median Response Time") or 0)
    except Exception:
        pass

    p50_ms = None
    p95_ms = None
    p99_ms = None
    try:
        p50_ms = float(col("50%") or 0)
    except Exception:
        try:
            median_ms = float(col("Median Response Time") or 0)
            p50_ms = median_ms
        except Exception:
            pass

    try:
        p95_ms = float(col("95%") or 0)
    except Exception:
        pass

    try:
        p99_ms = float(col("99%") or 0)
    except Exception:
        pass

    rps = None
    try:
        rps = float(col("Requests/s") or 0)
    except Exception:
        pass

    p50_sec = round(p50_ms / 1000, 2) if p50_ms is not None else None
    p95_sec = round(p95_ms / 1000, 2) if p95_ms is not None else None
    p99_sec = round(p99_ms / 1000, 2) if p99_ms is not None else None

    stats.update({
        "median_latency": p50_sec,
        "p95_latency": p95_sec,
        "p99_latency": p99_sec,
        "rps": rps,
        "total_requests": total_requests,
        "total_failures": total_failures,
    })

    # Fail loudly if Locust CSV shows 0 requests
    if stats["total_requests"] is not None and stats["total_requests"] == 0:
        raise RuntimeError(
            "FAIL: Locust produced 0 requests in " + run_time
            " - likely the mock server was not ready when Locust started. "
            "Check the mock server logs and the 'wait_for_server' timeout."
        )

    # Read before/after metrics snapshots from /metrics for cache-hit rate
    # and cost deltas per 1k requests.
    before = read_metrics_snapshot()
    after = read_metrics_snapshot()
    if before is not None and after is not None:
        dh = after["cache_hits"] - before["cache_hits"]
        dm = after["cache_misses"] - before["cache_misses"]
        total = dh + dm
        if total > 0:
            stats["cache_hit_rate"] = round(dh / total, 2)
        else:
            stats["cache_hit_rate"] = 0.0
        # Cost delta per 1k requests
        cost_delta = after["estimated_cost"] - before["estimated_cost"]
        stats["estimated_cost_per_1k"] = (
            round(cost_delta * 1000, 6) if cost_delta is not None else None)
    else:
        # Fall back to reading Redis cache-stats if /metrics unavailable
        try:
            import redis as redis_lib
            r = redis_lib.Redis(host="localhost", port=6379, db=15)
            after_hits = float(r.get("cache:stats:hits") or 0)
            after_misses = float(r.get("cache:stats:misses") or 0)
            total_cache = after_hits + after_misses
            if total_cache > 0:
                stats["cache_hit_rate"] = round(after_hits / total_cache, 2)
            else:
                stats["cache_hit_rate"] = 0.0
        except Exception:
            stats["cache_hit_rate"] = None

    # Estimate cost per 1k requests using the PRICING_TABLE from config
    try:
        from app.config import settings, compute_estimated_cost
        PROMPT_TOKENS = _env_int("MOCK_PROMPT_TOKENS", 20)
        COMPLETION_TOKENS = _env_int("MOCK_COMPLETION_TOKENS", 50)
        served_model = _env_str("OPENAI_PRIMARY_MODEL", "gpt-3.5-turbo")
        global_prompt_price = _env_float(
            "CHAT_PROMPT_PRICE_PER_MILLION", 0.001)
        global_comp_price = _env_float(
            "CHAT_COMPLETION_PRICE_PER_MILLION", 0.002)
        cost = compute_estimated_cost(
            served_model=served_model,
            prompt_tokens=PROMPT_TOKENS,
            completion_tokens=COMPLETION_TOKENS,
            pricing_table=settings.PRICING_TABLE,
            global_prompt_price=global_prompt_price,
            global_completion_price=global_comp_price,
        )
        stats["estimated_cost_per_1k"] = round(cost * 1000, 6)
    except Exception:
        pass

    return stats


def run_scenario(*, name, users, spawn_rate, run_time,
                 fallback_enabled, cache_off):
    # Start both servers
    mock_proc = start_mock_server()
    gateway_proc = start_gateway()

    # Wait for both servers to be ready
    wait_for_server(port=GATEWAY_PORT)

    env = os.environ.copy()
    env["MOCK_FAILURE_RATE"] = "30" if not fallback_enabled else "0"
    env["MOCK_FAILURE_TYPE"] = "5xx"
    env["MOCK_LATENCY_MEAN"] = "1.0" if fallback_enabled else "1.5"
    env["MOCK_LATENCY_JITTER"] = "0.2"
    flush_redis()
    csv_path = EVAL_DIR / "locust_output"
    try:
        stats = run_locust_csv(
            users=users, spawn_rate=spawn_rate, run_time=run_time,
            csv_path=csv_path, env_extra=env, cwd=str(EVAL_DIR),
        )
    finally:
        stop_mock_server(mock_proc)
        stop_gateway(gateway_proc)
    stats["fallback_enabled"] = fallback_enabled
    stats["cache_off"] = cache_off
    stats["scenario"] = name
    return stats


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = DOCS_DIR / "EVAL.md"

    cache_off = run_scenario(name="Cache OFF", users=10, spawn_rate=2, run_time="30s",
                             fallback_enabled=True, cache_off=True)
    cache_on = run_scenario(name="Cache ON", users=10, spawn_rate=2, run_time="30s",
                            fallback_enabled=True, cache_off=False)
    fallback_off = run_scenario(name="Fallback OFF", users=10, spawn_rate=2, run_time="30s",
                                fallback_enabled=False, cache_off=True)
    fallback_on = run_scenario(name="Fallback ON", users=10, spawn_rate=2, run_time="30s",
                               fallback_enabled=True, cache_off=True)
    hard_down = run_scenario(name="Hard-down", users=5, spawn_rate=1, run_time="45s",
                             fallback_enabled=False, cache_off=True)

    now = datetime.datetime.now().isoformat()

    def fmtnum(v):
        if v is not None:
            return "{:.2f}".format(v)
        return "N/A"

    def perr(s):
        if s["total_requests"] is not None and s["total_requests"] > 0:
            return "{:.1f}".format(s["total_failures"] / s["total_requests"] * 100)
        return "N/A"

    def chpct(s):
        if s["cache_hit_rate"] is not None:
            return "{:.1f}".format(s["cache_hit_rate"] * 100)
        return "N/A"

    ofb_off = "ON" if cache_off["fallback_enabled"] else "OFF"
    ofb_on = "ON" if cache_on["fallback_enabled"] else "OFF"
    fo_off = "ON" if fallback_off["fallback_enabled"] else "OFF"
    fo_on = "ON" if fallback_on["fallback_enabled"] else "OFF"
    hd_fb = "ON" if hard_down["fallback_enabled"] else "OFF"

    lines = [
        "# Phase-5 – Reproducible Evaluation",
        "> Generated: " + now + "\n",
        "\n## Scenarios\n\n",
        "| Scenario | Cache | Fallback | Median latency (s) | P95 latency (s) | P99 latency (s) | RPS | Error % | Cache hit % | Fallback % | Cost / 1k requests |\n",
        "|----------|-------|----------|-------------------|----------------|----------------|-----|---------|-------------|------------|-------------------|\n",
        "| " + cache_off["scenario"] + " | OFF | **" + ofb_off + "** | "
            + fmtnum(cache_off["median_latency"]) + " | "
            + fmtnum(cache_off["p95_latency"]) + " | "
            + fmtnum(cache_off["p99_latency"]) + " | "
            + fmtnum(cache_off["rps"]) + " | "
            + perr(cache_off) + " | "
            + chpct(cache_off) + " | N/A | "
            + fmtnum(cache_off["estimated_cost_per_1k"]) + " |\n",
        "| " + cache_on["scenario"] + " | ON | **" + ofb_on + "** | "
            + fmtnum(cache_on["median_latency"]) + " | "
            + fmtnum(cache_on["p95_latency"]) + " | "
            + fmtnum(cache_on["p99_latency"]) + " | "
            + fmtnum(cache_on["rps"]) + " | "
            + perr(cache_on) + " | "
            + chpct(cache_on) + " | N/A | "
            + fmtnum(cache_on["estimated_cost_per_1k"]) + " |\n",
        "| " + fallback_off["scenario"] + " | OFF | **" + fo_off + "** | "
            + fmtnum(fallback_off["median_latency"]) + " | "
            + fmtnum(fallback_off["p95_latency"]) + " | "
            + fmtnum(fallback_off["p99_latency"]) + " | "
            + fmtnum(fallback_off["rps"]) + " | "
            + perr(fallback_off) + " | "
            + chpct(fallback_off) + " | "
            + str(fallback_off["total_failures"]) + " / " + str(fallback_off["total_requests"]) + " | "
            + fmtnum(fallback_off["estimated_cost_per_1k"]) + " |\n",
        "| " + fallback_on["scenario"] + " | OFF | **" + fo_on + "** | "
            + fmtnum(fallback_on["median_latency"]) + " | "
            + fmtnum(fallback_on["p95_latency"]) + " | "
            + fmtnum(fallback_on["p99_latency"]) + " | "
            + fmtnum(fallback_on["rps"]) + " | "
            + perr(fallback_on) + " | "
            + chpct(fallback_on) + " | "
            + str(fallback_on["total_failures"]) + " / " + str(fallback_on["total_requests"]) + " | "
            + fmtnum(fallback_on["estimated_cost_per_1k"]) + " |\n",
        "| " + hard_down["scenario"] + " | OFF | **" + hd_fb + "** | "
            + fmtnum(hard_down["median_latency"]) + " | "
            + fmtnum(hard_down["p95_latency"]) + " | "
            + fmtnum(hard_down["p99_latency"]) + " | "
            + fmtnum(hard_down["rps"]) + " | "
            + perr(hard_down) + " | "
            + chpct(hard_down) + " | N/A | "
            + fmtnum(hard_down["estimated_cost_per_1k"]) + " |\n",
    ]
    md_path.write_text("\n".join(lines))
    print("Evaluation written to " + str(md_path))

    print("--- Exact commands ---")
    print("# 1. Start mock server (once, background):")
    print("   python -m uvicorn eval.mock_openai:app --host 0.0.0.0 --port " + str(MOCK_SERVER_PORT) + " &\n")
    print("# 2. Start gateway (once, background):")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port " + str(GATEWAY_PORT) + " &\n")
    print("# 3. Run the evaluation driver (generates docs/EVAL.md):")
    print("   python -m eval.run_eval\n")
    print("# 4. Redis was flushed (DB 15) between every scenario to keep counters clean.\n")
    print("# 5. Provider is a mock OpenAI server (eval.mock_openai) – not a real LLM.\n")


if __name__ == "__main__":
    main()