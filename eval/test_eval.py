#!/usr/bin/env python3
import subprocess, sys, time, os, httpx, pathlib

# Clean kill any python processes
os.system('taskkill /f /im python.exe 2>nul')
time.sleep(2)

# Start mock server
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'eval.mock_openai:app', '--host', '0.0.0.0', '--port', '8001'],
    cwd='eval', stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

# Wait for server to be ready
print('Waiting for server...')
for i in range(15):
    try:
        r = httpx.get('http://127.0.0.1:8001/health', timeout=2)
        print(f'Server ready after {i+1} attempts')
        break
    except Exception as e:
        time.sleep(1)
        if i == 14:
            print(f'Server not ready after 15 attempts. Error: {e}')
            proc.terminate()
            sys.exit(1)

print('Server is running!')
print('Running Locust...')

# Run locust
cmd = [
    sys.executable, '-m', 'locust',
    '-f', 'locustfile.py',
    '--headless',
    '--csv', 'locust_output',
    '--host', 'http://127.0.0.1:8001',
    '--users', '10',
    '--spawn-rate', '2',
    '--run-time', '30s',
]
result = subprocess.run(cmd, capture_output=True, text=True, cwd='eval')
print(f'Locust exit code: {result.returncode}')
print(f'Locust stderr (last 200): {result.stderr[-200:]}')

# Check CSV
csv_path = pathlib.Path('eval/locust_output_stats.csv')
print(f'CSV exists: {csv_path.exists()')
size = csv_path.stat().st_size if csv_path.exists() else 0
print(f'CSV size: {size}')

if csv_path.exists():
    with open(csv_path) as f:
        for i, line in enumerate(f):
            if i < 8:
                print(f'Line {i}:', line.rstrip())

# Kill server
proc.terminate()
proc.wait(timeout=5)
print('Done')