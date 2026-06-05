from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Header, HTTPException, Query

from app.models.f1 import F1DataSource, F1LiveReadiness, F1Race, F1SeasonSchedule, F1Session
from app.config import settings
from app.services.f1_model_service import F1ModelService
from app.services.f1_refresh_service import F1RefreshService
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


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_f1_data(
    season: str = Query(default="current"),
    include_results: bool = Query(default=True),
    rebuild_features: bool = Query(default=True),
    rebuild_training: bool = Query(default=True),
    refresh_live_sessions: bool = Query(default=True),
    retrain_models: bool = Query(default=False),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        normalized_season: int | str = "current" if season == "current" else int(season)
        return F1RefreshService.refresh_season(
            season=normalized_season,
            include_results=include_results,
            rebuild_features=rebuild_features,
            rebuild_training=rebuild_training,
            refresh_live_sessions=refresh_live_sessions,
            retrain_models=retrain_models,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="season must be a year or 'current'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/ingest/sessions/{session_key}/events", response_model=Dict[str, Any])
async def ingest_f1_session_events(
    session_key: int,
    include_race_control: bool = Query(default=True),
    include_weather: bool = Query(default=True),
    limit: int = Query(default=500, ge=1, le=1000),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.ingest_session_events(
            session_key=session_key,
            include_race_control=include_race_control,
            include_weather=include_weather,
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


@router.post("/ingest/sessions/{session_key}/driver-snapshots", response_model=Dict[str, Any])
async def ingest_f1_driver_session_snapshots(
    session_key: int,
    position_limit: int = Query(default=1500, ge=1, le=5000),
    lap_limit: int = Query(default=1500, ge=1, le=5000),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.ingest_driver_session_snapshots(
            session_key=session_key,
            position_limit=position_limit,
            lap_limit=lap_limit,
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="OpenF1 returned an error")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/sessions/{session_key}/snapshots/build", response_model=Dict[str, Any])
async def build_f1_session_feature_snapshots(
    session_key: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.build_session_feature_snapshots(session_key)
    except HTTPException:
        raise
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


@router.post("/sessions/seasons/{season}/race-links/build", response_model=Dict[str, Any])
async def build_f1_session_race_links(
    season: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.build_session_race_links(season)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/seasons/{season}/race-links", response_model=List[Dict[str, Any]])
async def get_f1_session_race_links(
    season: int,
    limit: int = Query(default=500, ge=1, le=1000),
):
    try:
        return F1StorageService.list_session_race_links(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/sessions/{session_key}/events", response_model=List[Dict[str, Any]])
async def get_stored_f1_session_events(
    session_key: int,
    event_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
):
    try:
        if event_type and event_type not in {"race_control", "weather"}:
            raise HTTPException(status_code=400, detail="event_type must be race_control or weather")
        return F1StorageService.list_session_events(session_key, event_type, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stored/sessions/{session_key}/driver-snapshots", response_model=List[Dict[str, Any]])
async def get_stored_f1_driver_session_snapshots(
    session_key: int,
    limit: int = Query(default=100, ge=1, le=250),
):
    try:
        return F1StorageService.list_driver_session_snapshots(session_key, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/sessions/{session_key}/snapshots", response_model=List[Dict[str, Any]])
async def get_f1_session_feature_snapshots(
    session_key: int,
    subject_type: str | None = Query(default=None),
    subject_key: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=500),
):
    try:
        if subject_type and subject_type not in {"session", "driver", "constructor"}:
            raise HTTPException(status_code=400, detail="subject_type must be session, driver, or constructor")
        return F1StorageService.list_feature_snapshots(session_key, subject_type, subject_key, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/sessions/{session_key}/build", response_model=Dict[str, Any])
async def build_f1_session_predictions(
    session_key: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1ModelService.predict_session(session_key=session_key, persist=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/sessions/{session_key}", response_model=Dict[str, Any])
async def get_f1_session_predictions(
    session_key: int,
):
    try:
        return F1ModelService.predict_session(session_key=session_key, persist=False)
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


@router.post("/features/seasons/{season}/constructors/build", response_model=Dict[str, Any])
async def build_f1_constructor_season_features(
    season: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.build_constructor_season_features(season)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/seasons/{season}/constructors", response_model=List[Dict[str, Any]])
async def get_f1_constructor_season_features(
    season: int,
    limit: int = Query(default=100, ge=1, le=250),
):
    try:
        return F1StorageService.list_constructor_season_features(season, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/seasons/{season}/examples/build", response_model=Dict[str, Any])
async def build_f1_training_examples(
    season: int,
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1StorageService.build_training_examples(season)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/seasons/{season}/examples", response_model=List[Dict[str, Any]])
async def get_f1_training_examples(
    season: int,
    outcome_type: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=2000),
):
    try:
        if outcome_type and outcome_type not in {"points_finish", "podium_finish"}:
            raise HTTPException(status_code=400, detail="outcome_type must be points_finish or podium_finish")
        return F1StorageService.list_training_examples(season, outcome_type, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/seasons/{season}/{outcome_type}/train", response_model=Dict[str, Any])
async def train_f1_baseline_model(
    season: int,
    outcome_type: str,
    eval_start_round: int = Query(default=19, ge=2, le=30),
    admin_token: str | None = Header(default=None, alias="x-atris-admin-token"),
):
    try:
        require_admin_token(admin_token)
        return F1ModelService.train_baseline(
            season=season,
            outcome_type=outcome_type,
            eval_start_round=eval_start_round,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/versions", response_model=List[Dict[str, Any]])
async def get_f1_model_versions(
    outcome_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        if outcome_type and outcome_type not in {"points_finish", "podium_finish"}:
            raise HTTPException(status_code=400, detail="outcome_type must be points_finish or podium_finish")
        return F1ModelService.list_model_versions(outcome_type, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/seasons/{season}/backtest", response_model=List[Dict[str, Any]])
async def get_f1_backtest_predictions(
    season: int,
    outcome_type: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=2000),
):
    try:
        if outcome_type and outcome_type not in {"points_finish", "podium_finish"}:
            raise HTTPException(status_code=400, detail="outcome_type must be points_finish or podium_finish")
        return F1ModelService.list_backtest_predictions(season, outcome_type, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/seasons/{season}/rounds/{round_number}", response_model=Dict[str, Any])
async def get_f1_race_predictions(
    season: int,
    round_number: int,
):
    try:
        return F1ModelService.predict_race(season, round_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/seasons/{season}/rounds/{round_number}/drivers/{driver_id}", response_model=Dict[str, Any])
async def get_f1_driver_prediction(
    season: int,
    round_number: int,
    driver_id: str,
):
    try:
        return F1ModelService.predict_driver(season, round_number, driver_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
