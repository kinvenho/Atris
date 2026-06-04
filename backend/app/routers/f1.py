from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Header, HTTPException, Query

from app.models.f1 import F1DataSource, F1LiveReadiness, F1Race, F1SeasonSchedule, F1Session
from app.config import settings
from app.services.f1_service import F1Service
from app.services.f1_storage_service import F1StorageService

router = APIRouter()


def require_admin_token(x_atris_admin_token: str | None) -> None:
    if settings.ENV != "production" and not settings.AGENT_ADMIN_TOKEN:
        return
    if not settings.AGENT_ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="AGENT_ADMIN_TOKEN is not configured")
    if x_atris_admin_token != settings.AGENT_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/sources", response_model=List[F1DataSource])
async def get_f1_sources():
    return F1Service.get_sources()


@router.get("/live-readiness", response_model=F1LiveReadiness)
async def get_live_readiness():
    return F1Service.get_live_readiness()


@router.post("/ingest/sources", response_model=List[Dict[str, Any]])
async def ingest_f1_sources(
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.seed_sources()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seasons/{season}/races", response_model=F1SeasonSchedule)
async def get_f1_schedule(season: str):
    try:
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1Service.get_schedule(normalized_season)
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="F1 schedule source returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"F1 schedule source unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/seasons/{season}/races", response_model=Dict[str, Any])
async def ingest_f1_schedule(
    season: str,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1StorageService.ingest_schedule(normalized_season)
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="F1 schedule source returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"F1 schedule source unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/seasons/{season}/races", response_model=List[Dict[str, Any]])
async def get_stored_f1_races(
    season: int,
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        return F1StorageService.list_races(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/races/upcoming", response_model=List[F1Race])
async def get_upcoming_f1_races(
    season: str = Query(default="current"),
    limit: int = Query(default=5, ge=1, le=25),
):
    try:
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1Service.get_upcoming_races(normalized_season, limit)
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="F1 schedule source returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"F1 schedule source unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/sessions", response_model=Dict[str, Any])
async def ingest_f1_sessions(
    year: int | None = Query(default=None, ge=2023),
    country_name: str | None = Query(default=None),
    session_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=250),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.ingest_sessions(
            year=year,
            country_name=country_name,
            session_type=session_type,
            limit=limit,
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="OpenF1 returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[F1Session])
async def get_f1_sessions(
    year: int | None = Query(default=None, ge=2023),
    country_name: str | None = Query(default=None),
    session_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=250),
):
    try:
        return F1Service.get_sessions(
            year=year,
            country_name=country_name,
            session_type=session_type,
            limit=limit,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="OpenF1 returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/sessions", response_model=List[Dict[str, Any]])
async def get_stored_f1_sessions(
    year: int = Query(ge=2023),
    limit: int = Query(default=100, ge=1, le=250),
):
    try:
        return F1StorageService.list_sessions(year, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/seasons/{season}/race-results", response_model=Dict[str, Any])
async def ingest_f1_race_results(
    season: str,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1StorageService.ingest_race_results(normalized_season)
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="F1 race results source returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"F1 race results source unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/seasons/{season}/qualifying-results", response_model=Dict[str, Any])
async def ingest_f1_qualifying_results(
    season: str,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1StorageService.ingest_qualifying_results(normalized_season)
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="F1 qualifying results source returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"F1 qualifying results source unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/seasons/{season}/drivers/build", response_model=Dict[str, Any])
async def build_f1_driver_season_features(
    season: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.build_driver_season_features(season)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/seasons/{season}/race-results", response_model=List[Dict[str, Any]])
async def get_stored_f1_race_results(
    season: int,
    limit: int = Query(default=1000, ge=1, le=1000),
):
    try:
        return F1StorageService.list_race_results(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/seasons/{season}/qualifying-results", response_model=List[Dict[str, Any]])
async def get_stored_f1_qualifying_results(
    season: int,
    limit: int = Query(default=1000, ge=1, le=1000),
):
    try:
        return F1StorageService.list_qualifying_results(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/seasons/{season}/drivers", response_model=List[Dict[str, Any]])
async def get_f1_driver_season_features(
    season: int,
    limit: int = Query(default=100, ge=1, le=250),
):
    try:
        return F1StorageService.list_driver_season_features(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
