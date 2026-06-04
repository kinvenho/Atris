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
    def _stamp_source_row(row: Dict[str, Any]) -> Dict[str, Any]:
        stamped = dict(row)
        stamped["source_name"] = "Jolpica-F1"
        stamped["fetched_at"] = datetime.now(timezone.utc).isoformat()
        stamped["updated_at"] = datetime.now(timezone.utc).isoformat()
        return stamped

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
