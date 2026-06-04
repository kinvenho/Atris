import logging
from datetime import datetime, timezone
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
