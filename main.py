from fastapi import FastAPI, Request
import time
import requests

app = FastAPI()

# Storage
logs = []
cache = {}

# -------------------- MIDDLEWARE --------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    log = {
        "path": request.url.path,
        "method": request.method,
        "time": round(process_time, 4)
    }

    # avoid logging internal endpoints
    if request.url.path not in ["/analytics", "/run-tests"]:
        logs.append(log)

    return response


# -------------------- ROUTES --------------------

@app.get("/")
def home():
    return {"message": "API Optimizer is running"}


@app.get("/test")
def test():
    # check cache
    if "test" in cache:
        return {
            "status": "working",
            "source": "cache"
        }

    # simulate slow API
    time.sleep(1)

    response = {
        "status": "working",
        "source": "server"
    }

    cache["test"] = response

    return response


@app.get("/logs")
def get_logs():
    return {"logs": logs}


@app.get("/analytics")
def get_analytics():
    total_requests = len(logs)

    endpoint_count = {}
    endpoint_time = {}

    slowest = {"path": "", "time": 0}

    for log in logs:
        path = log["path"]
        time_taken = log["time"]

        # count hits
        endpoint_count[path] = endpoint_count.get(path, 0) + 1
        endpoint_time[path] = endpoint_time.get(path, 0) + time_taken

        # find slowest
        if time_taken > slowest["time"]:
            slowest = log

    # calculate averages + suggestions
    avg_time = {}
    suggestions = {}

    for path in endpoint_count:
        avg = endpoint_time[path] / endpoint_count[path]
        avg_time[path] = round(avg, 4)

        if avg > 0.005:
            suggestions[path] = "⚠️ Slow API - needs optimization"
        else:
            suggestions[path] = "✅ Good performance"

    return {
        "total_requests": total_requests,
        "endpoint_hits": endpoint_count,
        "average_time": avg_time,
        "slowest_api": slowest,
        "suggestions": suggestions
    }


@app.get("/run-tests")
def run_tests():
    base_url = "http://127.0.0.1:8000"

    endpoints = ["/", "/test", "/test", "/"]

    results = []

    for ep in endpoints:
        res = requests.get(base_url + ep)
        results.append(res.json())

    return {
        "message": "All APIs tested",
        "results": results
    }