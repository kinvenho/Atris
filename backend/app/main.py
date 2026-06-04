from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_cors_origins

app = FastAPI(
    title="Atris API",
    description="Atris F1 Prediction Market Analytics API",
    version="1.0.0"
)

# CORS middleware for Next.js frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Atris API",
        "version": "1.0.0"
    }

from app.routers import recommendations, agent
from app.routers import f1
from app.services.scoring_service import ScoringService
from fastapi import HTTPException

# Register routers
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(f1.router, prefix="/f1", tags=["Formula 1"])

@app.get("/performance")
async def get_performance_snapshot():
    """
    GET /performance - Returns the latest performance scoreboard snapshot.
    """
    try:
        snapshot = ScoringService.get_latest_snapshot()
        if not snapshot:
            return {
                "total_predictions": 0,
                "correct": 0,
                "incorrect": 0,
                "pending": 0,
                "accuracy_rate": 0.0,
                "average_edge": 0.0,
                "snapshot_at": None,
            }
        return snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
