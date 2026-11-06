#!/usr/bin/env python3
import os, subprocess, sys, time, pathlib

os.environ["MOCK_FAILURE_RATE"] = "0"
os.environ["MOCK_FAILURE_TYPE"] = "none"
os.environ["MOCK_LATENCY_MEAN"] = "1.0"
os.environ["MOCK_LATENCY_JITTER"] = "0.2"

eval_dir = r"C:\Users\LENOVO\Downloads\API-Latency-reducer-main (1)\API-Latency-reducer-main\eval"

# Start mock server
mock = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "eval.mock_openai:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=eval_dir,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
time.sleep(2)

# Run locust
cmd = [
    sys.executable, "-m", "locust",
    "-f", "locustfile.py",
    "--headless",
    "--csv", "locust_output",
    "--host", "http://127.0.0.1:8001",
    "--users", "10",
    "--spawn-rate", "2",
    "--run-time", "30s",
]
proc = subprocess.run(cmd, capture_output=True, text=True, cwd=eval_dir)
print("Locust return code:", proc.returncode)
print("STDERR last 300:", proc.stderr[-300:])

csv_path = pathlib.Path(eval_dir) / "locust_output_stats.csv"
print("CSV exists:", csv_path.exists())
if csv_path.exists():
    print("CSV size:", csv_path.stat().st_size, "bytes")
    with open(csv_path) as f:
        for i, line in enumerate(f):
            if i < 8:
                print("  Line", i, ":", line.rstrip())

# Kill mock server
mock.terminate()
mock.wait(timeout=5)
print("Done")