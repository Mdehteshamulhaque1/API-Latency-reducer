#!/usr/bin/env python3
import os, subprocess, time, httpx, sys
# Set env vars
os.environ["MOCK_FAILURE_RATE"] = "0"
os.environ["MOCK_FAILURE_TYPE"] = "5xx"
os.environ["MOCK_LATENCY_MEAN"] = "1.0"
os.environ["MOCK_LATENCY_JITTER"] = "0.2"
os.environ["MOCK_PROMPT_PRICE_PER_MILLION"] = "0.001"
os.environ["MOCK_COMPLETION_PRICE_PER_MILLION"] = "0.002"

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "eval.mock_openai:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd="C:\\Users\\LENOVO\\Downloads\\API-Latency-reducer-main (1)\\API-Latency-reducer-main\\eval",
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
time.sleep(2)

try:
    r = httpx.post("http://127.0.0.1:8001/v1/chat/completions",
                   json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hello"}], "temperature": 0}, timeout=5)
    print("Status:", r.status_code)
    print("Body:", r.json())
except Exception as e:
    print("Error:", e)
finally:
    proc.terminate()
    proc.wait()
    print("Server stopped")