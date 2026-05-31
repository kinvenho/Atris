from fastapi import APIRouter, HTTPException, BackgroundTasks, Header, Query
from typing import List, Dict, Any
from app.services.supabase_client import get_supabase
from app.agent.runner import run_pipeline
from app.config import settings

router = APIRouter()

@router.get("/runs", response_model=List[Dict[str, Any]])
async def get_agent_runs():
    """
    GET /agent/runs - Fetches the history of recent pipeline runs.
    """
    try:
        supabase = get_supabase()
        response = supabase.table("agent_runs").select("*").order("started_at", desc=True).limit(20).execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def require_admin_token(x_atris_admin_token: str | None = Header(default=None)) -> None:
    if settings.ENV != "production" and not settings.AGENT_ADMIN_TOKEN:
        return
    if not settings.AGENT_ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="AGENT_ADMIN_TOKEN is not configured")
    if x_atris_admin_token != settings.AGENT_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=False),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    """
    POST /agent/trigger - Manually triggers the pipeline execution in the background.
    """
    try:
        require_admin_token(admin_token)
        if dry_run:
            return run_pipeline(dry_run=True)

        # Run pipeline asynchronously in background task to avoid blocking HTTP response
        background_tasks.add_task(run_pipeline, False)
        return {
            "status": "triggered",
            "message": "Pipeline run initiated in background."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
