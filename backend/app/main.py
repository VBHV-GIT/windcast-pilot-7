import os
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes.evaluation import router as evaluation_router

app = FastAPI(
    title="WindCast Analytics API",
    description="UK Wind Generation Forecast vs Outturn Evaluation Service (Elexon BMRS FUELHH & WINDFOR)",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
# In production, set CORS_ORIGINS to your frontend domain(s) (comma-separated):
# e.g. CORS_ORIGINS="https://windcast-analytics.vercel.app,http://localhost:3000"
# In local development if unset, defaults to standard local development origins (non-wildcard).
DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_cors_origins() -> List[str]:
    raw_env = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw_env:
        return DEFAULT_DEV_ORIGINS
    return [origin.strip() for origin in raw_env.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(evaluation_router, prefix="/api")


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "ok",
        "service": "windcast-analytics-backend",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    # Support dynamic PORT injection by hosting providers (defaults to 8000)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
