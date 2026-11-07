#!/usr/bin/env python3
import subprocess, sys, time, os, httpx, pathlib

# Start mock server from project root
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'eval.mock_openai:app', '--host', '0.0.0.0', '--port', '8001'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

time.sleep(3)

# Verify server is up
r = httpx.get('http://127.0.0.1:8001/health', timeout=5)
print(f'Server up: {r.status_code}')

# Run locust
cmd = [
    sys.executable, '-m', 'locust',
    '-f', 'eval/locustfile.py',
    '--headless',
    '--csv', 'eval/locust_output',
    '--host', 'http://127.0.0.1:8001',
    '--users', '10',
    '--spawn-rate', '2',
    '--run-time', '30s',
]
result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
print(f'Locust exit: {result.returncode}')
print(f'Locust stderr last 200: {result.stderr[-200:]}')

# Check CSV
csv_path = pathlib.Path('eval/locust_output_stats.csv')
print(f'CSV exists: {csv_path.exists()}, size: {csv_path.stat().st_size if csv_path.exists() else 0}')

if csv_path.exists():
    with open(csv_path) as f:
        for i, line in enumerate(f):
            if i < 8:
                print(f'Line {i}:', line.rstrip())

# Kill server
proc.terminate()
proc.wait(timeout=5)
print('Done')