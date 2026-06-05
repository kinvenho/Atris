import hashlib
import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List

from app.models.f1 import F1DataSource, F1Race, F1Session
from app.services.f1_service import F1Service
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class F1StorageService:
    @staticmethod
    def seed_sources() -> List[Dict[str, Any]]:
        sources = [F1StorageService._source_to_row(source) for source in F1Service.get_sources()]
        response = (
            get_supabase()
            .table("f1_sources")
            .upsert(sources, on_conflict="name")
            .execute()
        )
        return response.data or []

    @staticmethod
    def ingest_schedule(season: int | str = "current") -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Jolpica-F1",
            ingestion_type="schedule",
            metadata={"season": season},
        )
        try:
            schedule = F1Service.get_schedule(season)
            rows = [F1StorageService._race_to_row(race) for race in schedule.races]
            if rows:
                get_supabase().table("f1_races").upsert(rows, on_conflict="season,round").execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "Jolpica-F1",
                "season": schedule.season,
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 schedule ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def ingest_sessions(
        year: int | None = None,
        country_name: str | None = None,
        session_type: str | None = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        metadata = {
            "year": year,
            "country_name": country_name,
            "session_type": session_type,
            "limit": limit,
        }
        run_id = F1StorageService._start_ingestion_run(
            source_name="OpenF1",
            ingestion_type="sessions",
            metadata=metadata,
        )
        try:
            sessions = F1Service.get_sessions(
                year=year,
                country_name=country_name,
                session_type=session_type,
                limit=limit,
            )
            rows = [F1StorageService._session_to_row(session) for session in sessions]
            if rows:
                get_supabase().table("f1_sessions").upsert(rows, on_conflict="session_key").execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "OpenF1",
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 session ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def ingest_session_events(
        session_key: int,
        include_race_control: bool = True,
        include_weather: bool = True,
        limit: int = 500,
    ) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="OpenF1",
            ingestion_type="session_events",
            metadata={
                "session_key": session_key,
                "include_race_control": include_race_control,
                "include_weather": include_weather,
                "limit": limit,
            },
        )
        try:
            rows: List[Dict[str, Any]] = []
            if include_race_control:
                rows.extend(
                    F1StorageService._race_control_event_to_row(session_key, row)
                    for row in F1Service.get_race_control(session_key=session_key, limit=limit)
                )
            if include_weather:
                rows.extend(
                    F1StorageService._weather_event_to_row(session_key, row)
                    for row in F1Service.get_weather(session_key=session_key, limit=limit)
                )

            rows = [row for row in rows if row["event_key"]]
            if rows:
                get_supabase().table("f1_session_events").upsert(
                    rows,
                    on_conflict="event_key",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "OpenF1",
                "session_key": session_key,
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 session event ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def ingest_driver_session_snapshots(
        session_key: int,
        position_limit: int = 1500,
        lap_limit: int = 1500,
    ) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="OpenF1",
            ingestion_type="driver_session_snapshots",
            metadata={
                "session_key": session_key,
                "position_limit": position_limit,
                "lap_limit": lap_limit,
            },
        )
        try:
            positions = F1Service.get_position(session_key=session_key, limit=position_limit)
            laps = F1Service.get_laps(session_key=session_key, limit=lap_limit)
            rows = F1StorageService._driver_snapshot_rows(session_key, positions, laps)
            if rows:
                get_supabase().table("f1_driver_session_snapshots").upsert(
                    rows,
                    on_conflict="session_key,driver_number",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "OpenF1",
                "session_key": session_key,
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 driver session snapshot ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def ingest_race_results(season: int | str = "current") -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Jolpica-F1",
            ingestion_type="race_results",
            metadata={"season": season},
        )
        try:
            rows = F1Service.get_race_results(season)
            rows = [F1StorageService._stamp_source_row(row) for row in rows]
            if rows:
                get_supabase().table("f1_race_results").upsert(
                    rows,
                    on_conflict="season,round,driver_id",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "Jolpica-F1",
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 race results ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def ingest_qualifying_results(season: int | str = "current") -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Jolpica-F1",
            ingestion_type="qualifying_results",
            metadata={"season": season},
        )
        try:
            rows = F1Service.get_qualifying_results(season)
            rows = [F1StorageService._stamp_source_row(row) for row in rows]
            if rows:
                get_supabase().table("f1_qualifying_results").upsert(
                    rows,
                    on_conflict="season,round,driver_id",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "Jolpica-F1",
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 qualifying results ingestion failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def build_driver_season_features(season: int) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Atris",
            ingestion_type="driver_season_features",
            metadata={"season": season},
        )
        try:
            race_results = F1StorageService.list_race_results(season, limit=1000)
            qualifying_results = F1StorageService.list_qualifying_results(season, limit=1000)
            features = F1StorageService._build_driver_features(season, race_results, qualifying_results)
            if features:
                get_supabase().table("f1_driver_season_features").upsert(
                    features,
                    on_conflict="season,driver_id",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(features),
            )
            return {
                "status": "success",
                "source": "Atris",
                "season": season,
                "records_processed": len(features),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 driver feature build failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def build_constructor_season_features(season: int) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Atris",
            ingestion_type="constructor_season_features",
            metadata={"season": season},
        )
        try:
            race_results = F1StorageService.list_race_results(season, limit=1000)
            qualifying_results = F1StorageService.list_qualifying_results(season, limit=1000)
            features = F1StorageService._build_constructor_features(season, race_results, qualifying_results)
            if features:
                get_supabase().table("f1_constructor_season_features").upsert(
                    features,
                    on_conflict="season,constructor_id",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(features),
            )
            return {
                "status": "success",
                "source": "Atris",
                "season": season,
                "records_processed": len(features),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 constructor feature build failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def build_training_examples(season: int) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Atris",
            ingestion_type="model_training_examples",
            metadata={"season": season, "feature_set": "pre_race_v1"},
        )
        try:
            race_results = F1StorageService.list_race_results(season, limit=1000)
            qualifying_results = F1StorageService.list_qualifying_results(season, limit=1000)
            examples = F1StorageService._build_training_examples(season, race_results, qualifying_results)
            if examples:
                get_supabase().table("f1_model_training_examples").upsert(
                    examples,
                    on_conflict="season,round,driver_id,outcome_type,feature_set",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(examples),
            )
            return {
                "status": "success",
                "source": "Atris",
                "season": season,
                "records_processed": len(examples),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 training example build failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def build_session_feature_snapshots(session_key: int) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Atris",
            ingestion_type="session_feature_snapshots",
            metadata={"session_key": session_key, "feature_set": "race_weekend_v1"},
        )
        try:
            events = F1StorageService.list_session_events(session_key=session_key, limit=1000)
            driver_snapshots = F1StorageService.list_driver_session_snapshots(session_key=session_key, limit=250)
            rows = F1StorageService._build_session_feature_snapshots(session_key, events, driver_snapshots)
            if rows:
                get_supabase().table("f1_feature_snapshots").upsert(
                    rows,
                    on_conflict="session_key,subject_type,subject_key,feature_set",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "Atris",
                "session_key": session_key,
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 session feature snapshot build failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def build_session_race_links(season: int) -> Dict[str, Any]:
        run_id = F1StorageService._start_ingestion_run(
            source_name="Atris",
            ingestion_type="session_race_links",
            metadata={"season": season},
        )
        try:
            sessions = F1StorageService.list_sessions(season, limit=500)
            races = F1StorageService.list_races(season, limit=50)
            rows = F1StorageService._build_session_race_links(season, sessions, races)
            if rows:
                get_supabase().table("f1_session_race_links").upsert(
                    rows,
                    on_conflict="session_key",
                ).execute()
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="success",
                records_processed=len(rows),
            )
            return {
                "status": "success",
                "source": "Atris",
                "season": season,
                "records_processed": len(rows),
                "ingestion_run_id": run_id,
            }
        except Exception as e:
            logger.error("F1 session race link build failed: %s", e)
            F1StorageService._finish_ingestion_run(
                run_id=run_id,
                status="failed",
                records_processed=0,
                errors=[str(e)],
            )
            raise

    @staticmethod
    def list_races(season: int, limit: int = 50) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_races")
            .select("*")
            .eq("season", season)
            .order("round")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_sessions(year: int, limit: int = 100) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_sessions")
            .select("*")
            .eq("year", year)
            .order("date_start")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_session_events(
        session_key: int,
        event_type: str | None = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query = (
            get_supabase()
            .table("f1_session_events")
            .select("*")
            .eq("session_key", session_key)
            .order("event_time", desc=True)
            .limit(limit)
        )
        if event_type:
            query = query.eq("event_type", event_type)
        response = query.execute()
        return response.data or []

    @staticmethod
    def list_driver_session_snapshots(session_key: int, limit: int = 100) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_driver_session_snapshots")
            .select("*")
            .eq("session_key", session_key)
            .order("latest_position")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_feature_snapshots(
        session_key: int,
        subject_type: str | None = None,
        subject_key: str | None = None,
        limit: int = 250,
    ) -> List[Dict[str, Any]]:
        query = (
            get_supabase()
            .table("f1_feature_snapshots")
            .select("*")
            .eq("session_key", session_key)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if subject_type:
            query = query.eq("subject_type", subject_type)
        if subject_key:
            query = query.eq("subject_key", subject_key)
        response = query.execute()
        return response.data or []

    @staticmethod
    def list_session_race_links(season: int, limit: int = 500) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_session_race_links")
            .select("*")
            .eq("season", season)
            .order("round")
            .order("session_key")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_race_results(season: int, limit: int = 1000) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_race_results")
            .select("*")
            .eq("season", season)
            .order("round")
            .order("position_order")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_qualifying_results(season: int, limit: int = 1000) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_qualifying_results")
            .select("*")
            .eq("season", season)
            .order("round")
            .order("qualifying_position")
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_driver_season_features(season: int, limit: int = 100) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_driver_season_features")
            .select("*")
            .eq("season", season)
            .order("points", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_constructor_season_features(season: int, limit: int = 100) -> List[Dict[str, Any]]:
        response = (
            get_supabase()
            .table("f1_constructor_season_features")
            .select("*")
            .eq("season", season)
            .order("points", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    @staticmethod
    def list_training_examples(
        season: int,
        outcome_type: str | None = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        query = (
            get_supabase()
            .table("f1_model_training_examples")
            .select("*")
            .eq("season", season)
            .order("round")
            .limit(limit)
        )
        if outcome_type:
            query = query.eq("outcome_type", outcome_type)
        response = query.execute()
        return response.data or []

    @staticmethod
    def _start_ingestion_run(source_name: str, ingestion_type: str, metadata: Dict[str, Any]) -> str:
        response = (
            get_supabase()
            .table("f1_ingestion_runs")
            .insert({
                "source_name": source_name,
                "ingestion_type": ingestion_type,
                "status": "partial",
                "metadata": metadata,
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to create F1 ingestion run")
        return response.data[0]["id"]

    @staticmethod
    def _finish_ingestion_run(
        run_id: str,
        status: str,
        records_processed: int,
        errors: List[str] | None = None,
    ) -> None:
        get_supabase().table("f1_ingestion_runs").update({
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "records_processed": records_processed,
            "errors": errors or [],
        }).eq("id", run_id).execute()

    @staticmethod
    def _source_to_row(source: F1DataSource) -> Dict[str, Any]:
        return {
            "name": source.name,
            "kind": source.kind.value,
            "status": source.status.value,
            "access": source.access,
            "role": source.role,
            "notes": source.notes,
            "url": source.url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _race_to_row(race: F1Race) -> Dict[str, Any]:
        return {
            "season": race.season,
            "round": race.round,
            "race_name": race.race_name,
            "circuit_name": race.circuit_name,
            "locality": race.locality,
            "country": race.country,
            "race_date": race.date.isoformat() if race.date else None,
            "race_time": race.time,
            "source_name": "Jolpica-F1",
            "source_payload": race.raw,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _session_to_row(session: F1Session) -> Dict[str, Any]:
        return {
            "session_key": session.session_key,
            "meeting_key": session.meeting_key,
            "year": session.year,
            "session_name": session.session_name,
            "session_type": session.session_type,
            "country_name": session.country_name,
            "location": session.location,
            "circuit_short_name": session.circuit_short_name,
            "date_start": session.date_start.isoformat() if session.date_start else None,
            "date_end": session.date_end.isoformat() if session.date_end else None,
            "source_name": "OpenF1",
            "source_payload": session.raw,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _race_control_event_to_row(session_key: int, row: Dict[str, Any]) -> Dict[str, Any]:
        event_time = F1StorageService._parse_openf1_datetime(row.get("date"))
        return {
            "session_key": session_key,
            "event_key": F1StorageService._event_key("race_control", session_key, row),
            "event_type": "race_control",
            "event_time": event_time,
            "driver_number": F1StorageService._parse_int(row.get("driver_number")),
            "lap_number": F1StorageService._parse_int(row.get("lap_number")),
            "category": row.get("category"),
            "flag": row.get("flag"),
            "scope": row.get("scope"),
            "message": row.get("message"),
            "value": {},
            "source_name": "OpenF1",
            "source_payload": row,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _weather_event_to_row(session_key: int, row: Dict[str, Any]) -> Dict[str, Any]:
        event_time = F1StorageService._parse_openf1_datetime(row.get("date"))
        value = {
            "air_temperature": row.get("air_temperature"),
            "track_temperature": row.get("track_temperature"),
            "humidity": row.get("humidity"),
            "pressure": row.get("pressure"),
            "rainfall": row.get("rainfall"),
            "wind_direction": row.get("wind_direction"),
            "wind_speed": row.get("wind_speed"),
        }
        return {
            "session_key": session_key,
            "event_key": F1StorageService._event_key("weather", session_key, row),
            "event_type": "weather",
            "event_time": event_time,
            "driver_number": None,
            "lap_number": None,
            "category": "weather",
            "flag": None,
            "scope": None,
            "message": F1StorageService._weather_message(value),
            "value": value,
            "source_name": "OpenF1",
            "source_payload": row,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _stamp_source_row(row: Dict[str, Any]) -> Dict[str, Any]:
        stamped = dict(row)
        stamped["source_name"] = "Jolpica-F1"
        stamped["fetched_at"] = datetime.now(timezone.utc).isoformat()
        stamped["updated_at"] = datetime.now(timezone.utc).isoformat()
        return stamped

    @staticmethod
    def _driver_snapshot_rows(
        session_key: int,
        positions: List[Dict[str, Any]],
        laps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        by_driver: Dict[int, Dict[str, Any]] = {}

        for position in positions:
            driver_number = F1StorageService._parse_int(position.get("driver_number"))
            if driver_number is None:
                continue
            snapshot = by_driver.setdefault(driver_number, F1StorageService._empty_driver_snapshot(session_key, driver_number))
            event_time = F1StorageService._parse_openf1_datetime(position.get("date"))
            if event_time and (snapshot["_latest_position_time"] is None or event_time >= snapshot["_latest_position_time"]):
                snapshot["latest_position"] = F1StorageService._parse_int(position.get("position"))
                snapshot["_latest_position_time"] = event_time
                snapshot["_latest_position_payload"] = position
            snapshot["position_samples"] += 1

        for lap in laps:
            driver_number = F1StorageService._parse_int(lap.get("driver_number"))
            if driver_number is None:
                continue
            snapshot = by_driver.setdefault(driver_number, F1StorageService._empty_driver_snapshot(session_key, driver_number))
            lap_number = F1StorageService._parse_int(lap.get("lap_number"))
            lap_duration = F1StorageService._parse_float(lap.get("lap_duration"))
            if lap_number is not None and (snapshot["latest_lap_number"] is None or lap_number > snapshot["latest_lap_number"]):
                snapshot["latest_lap_number"] = lap_number
                snapshot["_latest_lap_payload"] = lap
            if lap_duration is not None and (snapshot["fastest_lap_duration"] is None or lap_duration < snapshot["fastest_lap_duration"]):
                snapshot["fastest_lap_duration"] = lap_duration
            snapshot["lap_count"] += 1

        rows: List[Dict[str, Any]] = []
        for snapshot in by_driver.values():
            latest_position_payload = snapshot.pop("_latest_position_payload") or {}
            latest_lap_payload = snapshot.pop("_latest_lap_payload") or {}
            latest_position_time = snapshot.pop("_latest_position_time")
            snapshot["metrics"] = {
                "latest_position_at": latest_position_time,
                "latest_lap_duration": latest_lap_payload.get("lap_duration"),
                "duration_sector_1": latest_lap_payload.get("duration_sector_1"),
                "duration_sector_2": latest_lap_payload.get("duration_sector_2"),
                "duration_sector_3": latest_lap_payload.get("duration_sector_3"),
                "i1_speed": latest_lap_payload.get("i1_speed"),
                "i2_speed": latest_lap_payload.get("i2_speed"),
                "st_speed": latest_lap_payload.get("st_speed"),
            }
            snapshot["source_payload"] = {
                "latest_position": latest_position_payload,
                "latest_lap": latest_lap_payload,
            }
            snapshot["fetched_at"] = datetime.now(timezone.utc).isoformat()
            snapshot["updated_at"] = datetime.now(timezone.utc).isoformat()
            rows.append(snapshot)

        return rows

    @staticmethod
    def _empty_driver_snapshot(session_key: int, driver_number: int) -> Dict[str, Any]:
        return {
            "session_key": session_key,
            "driver_number": driver_number,
            "latest_position": None,
            "latest_lap_number": None,
            "fastest_lap_duration": None,
            "lap_count": 0,
            "position_samples": 0,
            "_latest_position_time": None,
            "_latest_position_payload": None,
            "_latest_lap_payload": None,
        }

    @staticmethod
    def _build_session_feature_snapshots(
        session_key: int,
        events: List[Dict[str, Any]],
        driver_snapshots: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        weather_events = [event for event in events if event.get("event_type") == "weather"]
        race_control_events = [event for event in events if event.get("event_type") == "race_control"]
        weather_summary = F1StorageService._weather_summary(weather_events)
        race_control_summary = F1StorageService._race_control_summary(race_control_events)
        driver_event_counts = F1StorageService._driver_event_counts(race_control_events)
        latest_event_time = F1StorageService._latest_event_time(events)
        fetched_at = datetime.now(timezone.utc).isoformat()

        rows: List[Dict[str, Any]] = []
        for snapshot in driver_snapshots:
            driver_number = snapshot.get("driver_number")
            if driver_number is None:
                continue
            driver_key = str(driver_number)
            metrics = snapshot.get("metrics") or {}
            event_counts = driver_event_counts.get(driver_key, {})
            features = {
                "driver_number": F1StorageService._parse_int(driver_number),
                "latest_position": snapshot.get("latest_position"),
                "latest_lap_number": snapshot.get("latest_lap_number"),
                "fastest_lap_duration": F1StorageService._parse_float(snapshot.get("fastest_lap_duration")),
                "lap_count": snapshot.get("lap_count") or 0,
                "position_samples": snapshot.get("position_samples") or 0,
                "latest_lap_duration": F1StorageService._parse_float(metrics.get("latest_lap_duration")),
                "sector_1": F1StorageService._parse_float(metrics.get("duration_sector_1")),
                "sector_2": F1StorageService._parse_float(metrics.get("duration_sector_2")),
                "sector_3": F1StorageService._parse_float(metrics.get("duration_sector_3")),
                "speed_trap": F1StorageService._parse_float(metrics.get("st_speed")),
                "race_control_events_for_driver": event_counts.get("total", 0),
                "yellow_flags_for_driver": event_counts.get("yellow", 0),
                "red_flags_for_driver": event_counts.get("red", 0),
                "session_race_control_events": race_control_summary["total_events"],
                "session_yellow_flags": race_control_summary["yellow_flags"],
                "session_red_flags": race_control_summary["red_flags"],
                "session_safety_car_events": race_control_summary["safety_car_events"],
                "latest_air_temperature": weather_summary.get("latest_air_temperature"),
                "latest_track_temperature": weather_summary.get("latest_track_temperature"),
                "latest_rainfall": weather_summary.get("latest_rainfall"),
                "avg_air_temperature": weather_summary.get("avg_air_temperature"),
                "avg_track_temperature": weather_summary.get("avg_track_temperature"),
                "rain_samples": weather_summary.get("rain_samples"),
            }
            rows.append({
                "session_key": session_key,
                "subject_type": "driver",
                "subject_key": driver_key,
                "snapshot_mode": "race_weekend",
                "feature_set": "race_weekend_v1",
                "features": features,
                "source_freshness": {
                    "latest_event_time": latest_event_time,
                    "driver_snapshot_fetched_at": snapshot.get("fetched_at"),
                    "built_at": fetched_at,
                },
                "updated_at": fetched_at,
            })

        return rows

    @staticmethod
    def _build_session_race_links(
        season: int,
        sessions: List[Dict[str, Any]],
        races: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for session in sessions:
            session_key = session.get("session_key")
            session_start = F1StorageService._parse_datetime_value(session.get("date_start"))
            if session_key is None or session_start is None:
                continue

            scored_races = [
                F1StorageService._score_session_race_match(session, race, session_start.date())
                for race in races
            ]
            scored_races = [match for match in scored_races if match["confidence"] >= 0.55]
            if not scored_races:
                continue

            best_match = max(scored_races, key=lambda match: match["confidence"])
            race = best_match["race"]
            rows.append({
                "session_key": session_key,
                "season": season,
                "round": race.get("round"),
                "race_name": race.get("race_name"),
                "session_name": session.get("session_name"),
                "session_type": session.get("session_type"),
                "confidence": best_match["confidence"],
                "match_reason": best_match["match_reason"],
                "metadata": {
                    "session_country_name": session.get("country_name"),
                    "session_location": session.get("location"),
                    "session_circuit_short_name": session.get("circuit_short_name"),
                    "session_date_start": session.get("date_start"),
                    "race_country": race.get("country"),
                    "race_locality": race.get("locality"),
                    "race_circuit_name": race.get("circuit_name"),
                    "race_date": race.get("race_date"),
                    "date_delta_days": best_match["date_delta_days"],
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        return rows

    @staticmethod
    def _score_session_race_match(
        session: Dict[str, Any],
        race: Dict[str, Any],
        session_date: date,
    ) -> Dict[str, Any]:
        race_date = F1StorageService._parse_date_value(race.get("race_date"))
        if race_date is None:
            return {
                "race": race,
                "confidence": 0.0,
                "match_reason": "missing_race_date",
                "date_delta_days": None,
            }

        date_delta_days = abs((race_date - session_date).days)
        if date_delta_days <= 3:
            date_score = 0.55
        elif date_delta_days <= 6:
            date_score = 0.35
        else:
            date_score = 0.0

        session_country = F1StorageService._normalize_text(session.get("country_name"))
        race_country = F1StorageService._normalize_text(race.get("country"))
        country_score = 0.25 if session_country and race_country and session_country == race_country else 0.0

        location_text = " ".join([
            F1StorageService._normalize_text(session.get("location")),
            F1StorageService._normalize_text(session.get("circuit_short_name")),
        ]).strip()
        race_text = " ".join([
            F1StorageService._normalize_text(race.get("locality")),
            F1StorageService._normalize_text(race.get("circuit_name")),
        ]).strip()
        text_score = 0.0
        if location_text and race_text:
            location_tokens = {token for token in location_text.split() if len(token) >= 4}
            race_tokens = {token for token in race_text.split() if len(token) >= 4}
            if location_tokens.intersection(race_tokens):
                text_score = 0.15

        confidence = min(round(date_score + country_score + text_score, 4), 1.0)
        reason_parts = []
        if date_score:
            reason_parts.append(f"date_delta={date_delta_days}")
        if country_score:
            reason_parts.append("country")
        if text_score:
            reason_parts.append("location_text")
        return {
            "race": race,
            "confidence": confidence,
            "match_reason": ",".join(reason_parts) or "low_confidence",
            "date_delta_days": date_delta_days,
        }

    @staticmethod
    def _weather_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        values = [event.get("value") or {} for event in events]
        latest = values[0] if values else {}
        air_values = [F1StorageService._parse_float(value.get("air_temperature")) for value in values]
        track_values = [F1StorageService._parse_float(value.get("track_temperature")) for value in values]
        rain_values = [F1StorageService._parse_float(value.get("rainfall")) for value in values]
        return {
            "latest_air_temperature": F1StorageService._parse_float(latest.get("air_temperature")),
            "latest_track_temperature": F1StorageService._parse_float(latest.get("track_temperature")),
            "latest_rainfall": F1StorageService._parse_float(latest.get("rainfall")),
            "avg_air_temperature": F1StorageService._average([value for value in air_values if value is not None]),
            "avg_track_temperature": F1StorageService._average([value for value in track_values if value is not None]),
            "rain_samples": len([value for value in rain_values if value and value > 0]),
        }

    @staticmethod
    def _race_control_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        flags = [str(event.get("flag") or "").upper() for event in events]
        messages = [str(event.get("message") or "").lower() for event in events]
        return {
            "total_events": len(events),
            "yellow_flags": len([flag for flag in flags if "YELLOW" in flag]),
            "red_flags": len([flag for flag in flags if "RED" in flag]),
            "safety_car_events": len([message for message in messages if "safety car" in message or "vsc" in message]),
        }

    @staticmethod
    def _driver_event_counts(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        counts: Dict[str, Dict[str, int]] = {}
        for event in events:
            driver_number = event.get("driver_number")
            if driver_number is None:
                continue
            driver_key = str(driver_number)
            driver_counts = counts.setdefault(driver_key, {"total": 0, "yellow": 0, "red": 0})
            flag = str(event.get("flag") or "").upper()
            driver_counts["total"] += 1
            driver_counts["yellow"] += 1 if "YELLOW" in flag else 0
            driver_counts["red"] += 1 if "RED" in flag else 0
        return counts

    @staticmethod
    def _latest_event_time(events: List[Dict[str, Any]]) -> str | None:
        event_times = [event.get("event_time") for event in events if event.get("event_time")]
        return max(event_times) if event_times else None

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip().lower().replace("-", " ")

    @staticmethod
    def _build_driver_features(
        season: int,
        race_results: List[Dict[str, Any]],
        qualifying_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        by_driver: Dict[str, Dict[str, Any]] = {}

        for result in race_results:
            driver_id = result.get("driver_id")
            if not driver_id:
                continue
            feature = by_driver.setdefault(driver_id, F1StorageService._empty_driver_feature(season, result))
            position = result.get("position_order")
            points = float(result.get("points") or 0)
            grid = result.get("grid")
            status = str(result.get("status") or "").lower()

            feature["starts"] += 1
            feature["points"] += points
            feature["wins"] += 1 if position == 1 else 0
            feature["podiums"] += 1 if position is not None and position <= 3 else 0
            feature["points_finishes"] += 1 if position is not None and position <= 10 else 0
            feature["dnfs"] += 1 if not any(token in status for token in ["finished", "+", "lap"]) else 0
            feature["_position_sum"] += position or 0
            feature["_position_count"] += 1 if position is not None else 0
            feature["_grid_sum"] += grid or 0
            feature["_grid_count"] += 1 if grid is not None and grid > 0 else 0

        for qualifying in qualifying_results:
            driver_id = qualifying.get("driver_id")
            if not driver_id:
                continue
            feature = by_driver.setdefault(driver_id, F1StorageService._empty_driver_feature(season, qualifying))
            qualifying_position = qualifying.get("qualifying_position")
            feature["qualifying_sessions"] += 1
            feature["poles"] += 1 if qualifying_position == 1 else 0
            feature["q3_appearances"] += 1 if qualifying.get("q3") else 0
            feature["_qualifying_sum"] += qualifying_position or 0
            feature["_qualifying_count"] += 1 if qualifying_position is not None else 0

        built: List[Dict[str, Any]] = []
        for feature in by_driver.values():
            starts = max(feature["starts"], 1)
            feature["avg_finish_position"] = F1StorageService._safe_average(feature.pop("_position_sum"), feature.pop("_position_count"))
            feature["avg_grid_position"] = F1StorageService._safe_average(feature.pop("_grid_sum"), feature.pop("_grid_count"))
            feature["avg_qualifying_position"] = F1StorageService._safe_average(feature.pop("_qualifying_sum"), feature.pop("_qualifying_count"))
            feature["points_per_start"] = round(float(feature["points"]) / starts, 4)
            feature["podium_rate"] = round(float(feature["podiums"]) / starts, 4)
            feature["points_finish_rate"] = round(float(feature["points_finishes"]) / starts, 4)
            feature["dnf_rate"] = round(float(feature["dnfs"]) / starts, 4)
            feature["updated_at"] = datetime.now(timezone.utc).isoformat()
            built.append(feature)

        return built

    @staticmethod
    def _build_constructor_features(
        season: int,
        race_results: List[Dict[str, Any]],
        qualifying_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        by_constructor: Dict[str, Dict[str, Any]] = {}

        for result in race_results:
            constructor_id = result.get("constructor_id")
            if not constructor_id:
                continue
            feature = by_constructor.setdefault(
                constructor_id,
                F1StorageService._empty_constructor_feature(season, result),
            )
            position = result.get("position_order")
            points = float(result.get("points") or 0)
            grid = result.get("grid")
            status = str(result.get("status") or "").lower()

            feature["starts"] += 1
            feature["points"] += points
            feature["wins"] += 1 if position == 1 else 0
            feature["podiums"] += 1 if position is not None and position <= 3 else 0
            feature["points_finishes"] += 1 if position is not None and position <= 10 else 0
            feature["dnfs"] += 1 if not any(token in status for token in ["finished", "+", "lap"]) else 0
            feature["_drivers"].add(result.get("driver_id"))
            feature["_position_sum"] += position or 0
            feature["_position_count"] += 1 if position is not None else 0
            feature["_grid_sum"] += grid or 0
            feature["_grid_count"] += 1 if grid is not None and grid > 0 else 0

        for qualifying in qualifying_results:
            constructor_id = qualifying.get("constructor_id")
            if not constructor_id:
                continue
            feature = by_constructor.setdefault(
                constructor_id,
                F1StorageService._empty_constructor_feature(season, qualifying),
            )
            qualifying_position = qualifying.get("qualifying_position")
            feature["poles"] += 1 if qualifying_position == 1 else 0
            feature["q3_appearances"] += 1 if qualifying.get("q3") else 0
            feature["_qualifying_sum"] += qualifying_position or 0
            feature["_qualifying_count"] += 1 if qualifying_position is not None else 0

        built: List[Dict[str, Any]] = []
        for feature in by_constructor.values():
            starts = max(feature["starts"], 1)
            feature["driver_count"] = len([driver for driver in feature.pop("_drivers") if driver])
            feature["avg_finish_position"] = F1StorageService._safe_average(feature.pop("_position_sum"), feature.pop("_position_count"))
            feature["avg_grid_position"] = F1StorageService._safe_average(feature.pop("_grid_sum"), feature.pop("_grid_count"))
            feature["avg_qualifying_position"] = F1StorageService._safe_average(feature.pop("_qualifying_sum"), feature.pop("_qualifying_count"))
            feature["points_per_start"] = round(float(feature["points"]) / starts, 4)
            feature["podium_rate"] = round(float(feature["podiums"]) / starts, 4)
            feature["points_finish_rate"] = round(float(feature["points_finishes"]) / starts, 4)
            feature["dnf_rate"] = round(float(feature["dnfs"]) / starts, 4)
            feature["updated_at"] = datetime.now(timezone.utc).isoformat()
            built.append(feature)

        return built

    @staticmethod
    def _build_training_examples(
        season: int,
        race_results: List[Dict[str, Any]],
        qualifying_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        qualifying_by_race_driver = {
            (row.get("round"), row.get("driver_id")): row
            for row in qualifying_results
        }
        race_results_by_round: Dict[int, List[Dict[str, Any]]] = {}
        for result in race_results:
            round_number = result.get("round")
            if round_number is None:
                continue
            race_results_by_round.setdefault(round_number, []).append(result)

        driver_history: Dict[str, Dict[str, float]] = {}
        constructor_history: Dict[str, Dict[str, float]] = {}
        examples: List[Dict[str, Any]] = []

        for round_number in sorted(race_results_by_round):
            current_results = race_results_by_round[round_number]
            for result in current_results:
                driver_id = result.get("driver_id")
                constructor_id = result.get("constructor_id")
                if not driver_id:
                    continue

                qualifying = qualifying_by_race_driver.get((round_number, driver_id), {})
                driver_prior = F1StorageService._history_rates(driver_history.get(driver_id, {}))
                constructor_prior = F1StorageService._history_rates(constructor_history.get(constructor_id, {}))
                position = result.get("position_order")
                points_finish = bool(position is not None and position <= 10)
                podium_finish = bool(position is not None and position <= 3)

                features = {
                    "grid": result.get("grid"),
                    "qualifying_position": qualifying.get("qualifying_position"),
                    "q3": bool(qualifying.get("q3")),
                    "prior_driver_starts": driver_prior["starts"],
                    "prior_driver_points_per_start": driver_prior["points_per_start"],
                    "prior_driver_podium_rate": driver_prior["podium_rate"],
                    "prior_driver_points_finish_rate": driver_prior["points_finish_rate"],
                    "prior_driver_dnf_rate": driver_prior["dnf_rate"],
                    "prior_constructor_starts": constructor_prior["starts"],
                    "prior_constructor_points_per_start": constructor_prior["points_per_start"],
                    "prior_constructor_podium_rate": constructor_prior["podium_rate"],
                    "prior_constructor_points_finish_rate": constructor_prior["points_finish_rate"],
                    "prior_constructor_dnf_rate": constructor_prior["dnf_rate"],
                }
                source_result = {
                    "position_order": position,
                    "points": result.get("points"),
                    "status": result.get("status"),
                }
                for outcome_type, label in [
                    ("points_finish", points_finish),
                    ("podium_finish", podium_finish),
                ]:
                    examples.append({
                        "season": season,
                        "round": round_number,
                        "race_name": result.get("race_name"),
                        "driver_id": driver_id,
                        "driver_code": result.get("driver_code"),
                        "constructor_id": constructor_id,
                        "constructor_name": result.get("constructor_name"),
                        "outcome_type": outcome_type,
                        "label": label,
                        "feature_set": "pre_race_v1",
                        "features": features,
                        "source_result": source_result,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })

            for result in current_results:
                F1StorageService._update_history(driver_history, result.get("driver_id"), result)
                F1StorageService._update_history(constructor_history, result.get("constructor_id"), result)

        return examples

    @staticmethod
    def _empty_driver_feature(season: int, source: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "season": season,
            "driver_id": source.get("driver_id"),
            "driver_code": source.get("driver_code"),
            "driver_number": source.get("driver_number"),
            "given_name": source.get("given_name"),
            "family_name": source.get("family_name"),
            "constructor_id": source.get("constructor_id"),
            "constructor_name": source.get("constructor_name"),
            "starts": 0,
            "qualifying_sessions": 0,
            "points": 0.0,
            "wins": 0,
            "podiums": 0,
            "points_finishes": 0,
            "dnfs": 0,
            "poles": 0,
            "q3_appearances": 0,
            "_position_sum": 0,
            "_position_count": 0,
            "_grid_sum": 0,
            "_grid_count": 0,
            "_qualifying_sum": 0,
            "_qualifying_count": 0,
        }

    @staticmethod
    def _empty_constructor_feature(season: int, source: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "season": season,
            "constructor_id": source.get("constructor_id"),
            "constructor_name": source.get("constructor_name"),
            "starts": 0,
            "driver_count": 0,
            "points": 0.0,
            "wins": 0,
            "podiums": 0,
            "points_finishes": 0,
            "dnfs": 0,
            "poles": 0,
            "q3_appearances": 0,
            "_drivers": set(),
            "_position_sum": 0,
            "_position_count": 0,
            "_grid_sum": 0,
            "_grid_count": 0,
            "_qualifying_sum": 0,
            "_qualifying_count": 0,
        }

    @staticmethod
    def _update_history(history: Dict[str, Dict[str, float]], key: str | None, result: Dict[str, Any]) -> None:
        if not key:
            return
        state = history.setdefault(key, {
            "starts": 0,
            "points": 0.0,
            "podiums": 0,
            "points_finishes": 0,
            "dnfs": 0,
        })
        position = result.get("position_order")
        status = str(result.get("status") or "").lower()
        state["starts"] += 1
        state["points"] += float(result.get("points") or 0)
        state["podiums"] += 1 if position is not None and position <= 3 else 0
        state["points_finishes"] += 1 if position is not None and position <= 10 else 0
        state["dnfs"] += 1 if not any(token in status for token in ["finished", "+", "lap"]) else 0

    @staticmethod
    def _history_rates(state: Dict[str, float]) -> Dict[str, float]:
        starts = int(state.get("starts") or 0)
        if starts <= 0:
            return {
                "starts": 0,
                "points_per_start": 0.0,
                "podium_rate": 0.0,
                "points_finish_rate": 0.0,
                "dnf_rate": 0.0,
            }
        return {
            "starts": starts,
            "points_per_start": round(float(state.get("points") or 0) / starts, 4),
            "podium_rate": round(float(state.get("podiums") or 0) / starts, 4),
            "points_finish_rate": round(float(state.get("points_finishes") or 0) / starts, 4),
            "dnf_rate": round(float(state.get("dnfs") or 0) / starts, 4),
        }

    @staticmethod
    def _safe_average(total: float, count: int) -> float | None:
        if count <= 0:
            return None
        return round(float(total) / count, 4)

    @staticmethod
    def _average(values: List[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    @staticmethod
    def _event_key(event_type: str, session_key: int, row: Dict[str, Any]) -> str:
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return f"{event_type}:{session_key}:{digest}"

    @staticmethod
    def _weather_message(value: Dict[str, Any]) -> str:
        air = value.get("air_temperature")
        track = value.get("track_temperature")
        rain = value.get("rainfall")
        parts = []
        if air is not None:
            parts.append(f"air {air}C")
        if track is not None:
            parts.append(f"track {track}C")
        if rain is not None:
            parts.append(f"rain {rain}")
        return ", ".join(parts)

    @staticmethod
    def _parse_openf1_datetime(value: Any) -> str | None:
        if not value:
            return None
        clean_value = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_value).isoformat()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime_value(value: Any) -> datetime | None:
        if not value:
            return None
        clean_value = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_value)
        except ValueError:
            return None

    @staticmethod
    def _parse_date_value(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        clean_value = str(value).split("T")[0].split(" ")[0]
        try:
            return date.fromisoformat(clean_value)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
