from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="WindCast Analytics API",
    description="UK Wind Generation Forecast vs Outturn Evaluation Service",
    version="0.1.0",
)

# CORS configuration to allow local frontend development and production access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
