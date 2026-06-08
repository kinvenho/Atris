from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.f1_model_service import F1ModelService
from app.services.f1_storage_service import F1StorageService


class F1DashboardService:
    @staticmethod
    def race_payload(
        season: int,
        round_number: int,
        include_events: bool = True,
        event_limit: int = 50,
    ) -> Dict[str, Any]:
        race = F1DashboardService._race(season, round_number)
        session_links = F1StorageService.list_session_race_links(
            season,
            limit=100,
            round_number=round_number,
        )
        sessions = [
            F1DashboardService._session_payload(
                link,
                include_events=include_events,
                event_limit=event_limit,
            )
            for link in session_links
        ]

        pre_race_predictions = F1DashboardService._safe_pre_race_predictions(season, round_number)
        latest_session_prediction = F1DashboardService._latest_session_prediction(sessions)
        return {
            "season": season,
            "round": round_number,
            "race": race,
            "sessions": sessions,
            "pre_race_predictions": pre_race_predictions,
            "latest_race_weekend_predictions": latest_session_prediction,
            "freshness": F1DashboardService._freshness(race, sessions, pre_race_predictions, latest_session_prediction),
        }

    @staticmethod
    def _race(season: int, round_number: int) -> Dict[str, Any] | None:
        return F1StorageService.get_race(season, round_number)

    @staticmethod
    def _session_payload(
        link: Dict[str, Any],
        include_events: bool,
        event_limit: int,
    ) -> Dict[str, Any]:
        session_key = int(link["session_key"])
        events = F1StorageService.list_session_events(session_key, limit=event_limit) if include_events else []
        driver_snapshots = F1StorageService.list_driver_session_snapshots(session_key, limit=250)
        feature_snapshots = F1StorageService.list_feature_snapshots(
            session_key,
            subject_type="driver",
            limit=250,
        )
        predictions = F1DashboardService._safe_session_predictions(session_key)
        return {
            "session_key": session_key,
            "link": link,
            "events": events,
            "driver_snapshots": driver_snapshots,
            "feature_snapshots": feature_snapshots,
            "predictions": predictions,
            "freshness": {
                "latest_event_time": F1DashboardService._max_value(events, "event_time"),
                "latest_driver_snapshot_at": F1DashboardService._max_value(driver_snapshots, "updated_at"),
                "latest_feature_snapshot_at": F1DashboardService._max_value(feature_snapshots, "updated_at"),
                "latest_prediction_built_at": F1DashboardService._prediction_built_at(predictions),
            },
        }

    @staticmethod
    def _safe_pre_race_predictions(season: int, round_number: int) -> Dict[str, Any] | None:
        try:
            return F1ModelService.predict_race(season, round_number)
        except Exception:
            return None

    @staticmethod
    def _safe_session_predictions(session_key: int) -> Dict[str, Any] | None:
        try:
            return F1ModelService.predict_session(session_key, persist=False)
        except Exception:
            return None

    @staticmethod
    def _latest_session_prediction(sessions: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        sessions_with_predictions = [
            session for session in sessions
            if session.get("predictions")
        ]
        if not sessions_with_predictions:
            return None
        sessions_with_predictions.sort(
            key=lambda session: session.get("freshness", {}).get("latest_prediction_built_at") or "",
            reverse=True,
        )
        return sessions_with_predictions[0]["predictions"]

    @staticmethod
    def _freshness(
        race: Dict[str, Any] | None,
        sessions: List[Dict[str, Any]],
        pre_race_predictions: Dict[str, Any] | None,
        latest_session_prediction: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        session_freshness = [session.get("freshness") or {} for session in sessions]
        return {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "race_updated_at": (race or {}).get("updated_at"),
            "linked_sessions": len(sessions),
            "pre_race_prediction_count": len((pre_race_predictions or {}).get("predictions") or []),
            "race_weekend_prediction_count": len((latest_session_prediction or {}).get("predictions") or []),
            "latest_event_time": max(
                [item.get("latest_event_time") for item in session_freshness if item.get("latest_event_time")],
                default=None,
            ),
            "latest_feature_snapshot_at": max(
                [item.get("latest_feature_snapshot_at") for item in session_freshness if item.get("latest_feature_snapshot_at")],
                default=None,
            ),
            "latest_prediction_built_at": F1DashboardService._prediction_built_at(latest_session_prediction),
        }

    @staticmethod
    def _prediction_built_at(predictions: Dict[str, Any] | None) -> str | None:
        if not predictions:
            return None
        if predictions.get("generated_at"):
            return predictions["generated_at"]
        prediction_items = predictions.get("predictions") or []
        freshness_values = [
            ((item.get("features") or {}).get("source_freshness") or {}).get("built_at")
            for item in prediction_items
        ]
        return max([value for value in freshness_values if value], default=None)

    @staticmethod
    def _max_value(rows: List[Dict[str, Any]], key: str) -> str | None:
        values = [row.get(key) for row in rows if row.get(key)]
        return max(values) if values else None
