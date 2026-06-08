import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from app.config import settings
from app.services.f1_model_service import F1ModelService
from app.services.f1_storage_service import F1StorageService

logger = logging.getLogger(__name__)


class F1RefreshService:
    @staticmethod
    def refresh_season(
        season: int | str = "current",
        *,
        include_results: bool = True,
        rebuild_features: bool = True,
        rebuild_training: bool = True,
        retrain_models: bool = False,
        session_limit: int | None = None,
        refresh_live_sessions: bool = True,
        live_session_count: int | None = None,
    ) -> Dict[str, Any]:
        normalized_season = F1RefreshService._normalize_season(season)
        started_at = datetime.now(timezone.utc)
        steps: List[Dict[str, Any]] = []

        F1RefreshService._run_step(steps, "seed_sources", lambda: F1StorageService.seed_sources())
        F1RefreshService._run_step(steps, "ingest_schedule", lambda: F1StorageService.ingest_schedule(normalized_season))
        F1RefreshService._run_step(
            steps,
            "ingest_sessions",
            lambda: F1StorageService.ingest_sessions(
                year=normalized_season,
                limit=session_limit or settings.F1_REFRESH_SESSION_LIMIT,
            ),
        )
        F1RefreshService._run_step(
            steps,
            "derive_schedule_from_sessions",
            lambda: F1RefreshService._derive_schedule_if_missing(normalized_season),
        )
        F1RefreshService._run_step(
            steps,
            "build_session_race_links",
            lambda: F1StorageService.build_session_race_links(normalized_season),
        )

        if include_results:
            F1RefreshService._run_step(
                steps,
                "ingest_race_results",
                lambda: F1StorageService.ingest_race_results(normalized_season),
            )
            F1RefreshService._run_step(
                steps,
                "ingest_qualifying_results",
                lambda: F1StorageService.ingest_qualifying_results(normalized_season),
            )

        if rebuild_features:
            F1RefreshService._run_step(
                steps,
                "build_driver_features",
                lambda: F1StorageService.build_driver_season_features(normalized_season),
            )
            F1RefreshService._run_step(
                steps,
                "build_constructor_features",
                lambda: F1StorageService.build_constructor_season_features(normalized_season),
            )

        if rebuild_training:
            F1RefreshService._run_step(
                steps,
                "build_training_examples",
                lambda: F1StorageService.build_training_examples(normalized_season),
            )

        if refresh_live_sessions:
            for session_key in F1RefreshService._recent_session_keys(
                normalized_season,
                live_session_count or settings.F1_REFRESH_LIVE_SESSION_COUNT,
            ):
                F1RefreshService._refresh_session(steps, session_key)

        if retrain_models:
            F1RefreshService._run_step(
                steps,
                "train_points_finish_model",
                lambda: F1ModelService.train_baseline(normalized_season, "points_finish"),
            )
            F1RefreshService._run_step(
                steps,
                "train_podium_finish_model",
                lambda: F1ModelService.train_baseline(normalized_season, "podium_finish"),
            )

        failed_steps = [step for step in steps if step["status"] == "failed"]
        completed_at = datetime.now(timezone.utc)
        return {
            "status": "success" if not failed_steps else "partial",
            "season": normalized_season,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
            "steps": steps,
        }

    @staticmethod
    def refresh_current_weekend(
        season: int | str = "current",
        *,
        include_results: bool = True,
        rebuild_features: bool = True,
        rebuild_training: bool = True,
        session_limit: int | None = None,
    ) -> Dict[str, Any]:
        normalized_season = F1RefreshService._normalize_season(season)
        started_at = datetime.now(timezone.utc)
        steps: List[Dict[str, Any]] = []

        F1RefreshService._run_step(steps, "seed_sources", lambda: F1StorageService.seed_sources())
        F1RefreshService._run_step(steps, "ingest_schedule", lambda: F1StorageService.ingest_schedule(normalized_season))
        F1RefreshService._run_step(
            steps,
            "ingest_sessions",
            lambda: F1StorageService.ingest_sessions(
                year=normalized_season,
                limit=session_limit or settings.F1_REFRESH_SESSION_LIMIT,
            ),
        )
        F1RefreshService._run_step(
            steps,
            "derive_schedule_from_sessions",
            lambda: F1RefreshService._derive_schedule_if_missing(normalized_season),
        )
        F1RefreshService._run_step(
            steps,
            "build_session_race_links",
            lambda: F1StorageService.build_session_race_links(normalized_season),
        )

        if include_results:
            F1RefreshService._run_step(
                steps,
                "ingest_race_results",
                lambda: F1StorageService.ingest_race_results(normalized_season),
            )
            F1RefreshService._run_step(
                steps,
                "ingest_qualifying_results",
                lambda: F1StorageService.ingest_qualifying_results(normalized_season),
            )

        if rebuild_features:
            F1RefreshService._run_step(
                steps,
                "build_driver_features",
                lambda: F1StorageService.build_driver_season_features(normalized_season),
            )
            F1RefreshService._run_step(
                steps,
                "build_constructor_features",
                lambda: F1StorageService.build_constructor_season_features(normalized_season),
            )

        if rebuild_training:
            F1RefreshService._run_step(
                steps,
                "build_training_examples",
                lambda: F1StorageService.build_training_examples(normalized_season),
            )

        current_race = F1RefreshService._current_race(normalized_season)
        session_keys = F1RefreshService._round_session_keys(normalized_season, int((current_race or {}).get("round") or 0))
        for session_key in session_keys:
            F1RefreshService._refresh_session(steps, session_key)

        failed_steps = [step for step in steps if step["status"] == "failed"]
        completed_at = datetime.now(timezone.utc)
        return {
            "status": "success" if not failed_steps else "partial",
            "season": normalized_season,
            "round": (current_race or {}).get("round"),
            "race_name": (current_race or {}).get("race_name"),
            "session_keys": session_keys,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
            "steps": steps,
        }

    @staticmethod
    def _refresh_session(steps: List[Dict[str, Any]], session_key: int) -> None:
        F1RefreshService._run_step(
            steps,
            f"ingest_session_events:{session_key}",
            lambda session_key=session_key: F1StorageService.ingest_session_events(
                session_key=session_key,
                limit=settings.F1_LIVE_EVENT_LIMIT,
            ),
        )
        F1RefreshService._run_step(
            steps,
            f"ingest_driver_session_snapshots:{session_key}",
            lambda session_key=session_key: F1StorageService.ingest_driver_session_snapshots(
                session_key=session_key,
                position_limit=settings.F1_DRIVER_SNAPSHOT_LIMIT,
                lap_limit=settings.F1_DRIVER_SNAPSHOT_LIMIT,
            ),
        )
        F1RefreshService._run_step(
            steps,
            f"build_session_feature_snapshots:{session_key}",
            lambda session_key=session_key: F1StorageService.build_session_feature_snapshots(
                session_key=session_key,
            ),
        )
        F1RefreshService._run_step(
            steps,
            f"build_session_predictions:{session_key}",
            lambda session_key=session_key: F1ModelService.predict_session(
                session_key=session_key,
                persist=True,
            ),
        )

    @staticmethod
    def _run_step(
        steps: List[Dict[str, Any]],
        name: str,
        action: Callable[[], Any],
    ) -> None:
        started_at = datetime.now(timezone.utc)
        try:
            result = action()
            records_processed = F1RefreshService._records_processed(result)
            completed_at = datetime.now(timezone.utc)
            steps.append({
                "name": name,
                "status": "success",
                "records_processed": records_processed,
                "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
                "result": F1RefreshService._compact_result(result),
            })
        except Exception as e:
            logger.exception("F1 refresh step failed: %s", name)
            completed_at = datetime.now(timezone.utc)
            steps.append({
                "name": name,
                "status": "failed",
                "records_processed": 0,
                "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
                "error": str(e),
            })

    @staticmethod
    def _normalize_season(season: int | str) -> int:
        if isinstance(season, int):
            return season
        season_value = str(season).strip().lower()
        if season_value == "current":
            configured = str(settings.F1_REFRESH_SEASON).strip().lower()
            if configured and configured != "current":
                return int(configured)
            return datetime.now(timezone.utc).year
        return int(season_value)

    @staticmethod
    def _derive_schedule_if_missing(season: int) -> Dict[str, Any]:
        races = F1StorageService.list_races(season, limit=1)
        if races:
            return {
                "status": "skipped",
                "source": "OpenF1",
                "season": season,
                "records_processed": 0,
                "reason": "stored_schedule_exists",
            }
        return F1StorageService.derive_races_from_sessions(season)

    @staticmethod
    def _recent_session_keys(season: int, limit: int) -> List[int]:
        if limit <= 0:
            return []
        sessions = F1StorageService.list_sessions(season, limit=settings.F1_REFRESH_SESSION_LIMIT)
        sessions = [
            session for session in sessions
            if session.get("session_key") and session.get("session_type") in {"Race", "Qualifying", "Sprint", "Practice"}
        ]
        now = datetime.now(timezone.utc)
        available_sessions = [
            session for session in sessions
            if F1RefreshService._session_start(session) is not None
            and F1RefreshService._session_start(session) <= now
        ]
        upcoming_sessions = [
            session for session in sessions
            if F1RefreshService._session_start(session) is not None
            and F1RefreshService._session_start(session) > now
        ]

        available_sessions.sort(key=lambda session: F1RefreshService._session_start(session) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        upcoming_sessions.sort(key=lambda session: F1RefreshService._session_start(session) or datetime.max.replace(tzinfo=timezone.utc))
        selected_sessions = available_sessions if available_sessions else upcoming_sessions
        return [int(session["session_key"]) for session in selected_sessions[:limit]]

    @staticmethod
    def _current_race(season: int) -> Dict[str, Any] | None:
        races = F1StorageService.list_races(season, limit=100)
        if not races:
            return None

        now = datetime.now(timezone.utc)
        available_races = [
            race for race in races
            if F1RefreshService._race_start(race) is not None
            and F1RefreshService._race_start(race) <= now
        ]
        upcoming_races = [
            race for race in races
            if F1RefreshService._race_start(race) is not None
            and F1RefreshService._race_start(race) > now
        ]

        available_races.sort(key=lambda race: F1RefreshService._race_start(race) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        upcoming_races.sort(key=lambda race: F1RefreshService._race_start(race) or datetime.max.replace(tzinfo=timezone.utc))
        return (available_races or upcoming_races)[0] if (available_races or upcoming_races) else None

    @staticmethod
    def _round_session_keys(season: int, round_number: int) -> List[int]:
        if round_number <= 0:
            return []
        links = F1StorageService.list_session_race_links(season, limit=100, round_number=round_number)
        links.sort(key=lambda link: str((link.get("metadata") or {}).get("session_date_start") or ""))
        return [int(link["session_key"]) for link in links if link.get("session_key")]

    @staticmethod
    def _race_start(race: Dict[str, Any]) -> datetime | None:
        race_date = race.get("race_date")
        if not race_date:
            return None
        race_time = race.get("race_time") or "00:00:00Z"
        value = f"{race_date}T{race_time}"
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _session_start(session: Dict[str, Any]) -> datetime | None:
        value = session.get("date_start")
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _records_processed(result: Any) -> int:
        if isinstance(result, list):
            return len(result)
        if isinstance(result, dict):
            return int(result.get("records_processed") or result.get("backtest_predictions") or 0)
        return 0

    @staticmethod
    def _compact_result(result: Any) -> Dict[str, Any]:
        if isinstance(result, list):
            return {"records_processed": len(result)}
        if not isinstance(result, dict):
            return {}

        allowed_keys = {
            "status",
            "source",
            "season",
            "records_processed",
            "ingestion_run_id",
            "model_version_id",
            "model_name",
            "version",
            "outcome_type",
            "train_examples",
            "eval_examples",
            "backtest_predictions",
        }
        return {key: value for key, value in result.items() if key in allowed_keys}
