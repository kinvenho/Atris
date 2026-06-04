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
