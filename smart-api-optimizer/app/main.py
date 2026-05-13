from fastapi import FastAPI

from app.routes.api_routes import router as api_router

app = FastAPI(title="Smart API Optimizer")
app.include_router(api_router)


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "service": "smart-api-optimizer"}
