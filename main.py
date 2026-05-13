from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import requests

app = FastAPI()

# Allow browser access from file:// or other origins during local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (dashboard.html) from project root
app.mount("/static", StaticFiles(directory="."), name="static")

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
    # serve the dashboard UI
    try:
        return FileResponse("dashboard.html")
    except Exception:
        return JSONResponse({"message": "API Optimizer is running"})


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
        # some endpoints (like "/") return HTML; handle non-JSON safely
        try:
            results.append(res.json())
        except Exception:
            results.append({
                "status_code": res.status_code,
                "text": res.text[:1000]
            })

    return {
        "message": "All APIs tested",
        "results": results
    }