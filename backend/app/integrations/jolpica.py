from datetime import date
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models.f1 import F1Race, F1SeasonSchedule


class JolpicaClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.JOLPICA_BASE_URL).rstrip("/")

    def fetch_schedule(self, season: int | str = "current") -> F1SeasonSchedule:
        url = f"{self.base_url}/{season}/races.json"
        with httpx.Client(timeout=settings.F1_HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(url)
            response.raise_for_status()
        return self._parse_schedule(response.json())

    def fetch_race_results(self, season: int | str = "current") -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{season}/results.json"
        return self._fetch_paginated_rows(url, self._parse_race_results)

    def fetch_qualifying_results(self, season: int | str = "current") -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{season}/qualifying.json"
        return self._fetch_paginated_rows(url, self._parse_qualifying_results)

    def _parse_schedule(self, payload: Dict[str, Any]) -> F1SeasonSchedule:
        race_table = payload.get("MRData", {}).get("RaceTable", {})
        races = race_table.get("Races") or []
        parsed_races = [self._parse_race(race) for race in races]
        parsed_races = [race for race in parsed_races if race is not None]

        season_raw = race_table.get("season")
        if season_raw is None and parsed_races:
            season_raw = parsed_races[0].season

        return F1SeasonSchedule(
            season=int(season_raw or 0),
            races=parsed_races,
        )

    def _fetch_paginated_rows(self, url: str, parser) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        offset = 0
        limit = 100

        with httpx.Client(timeout=settings.F1_HTTP_TIMEOUT_SECONDS) as client:
            while True:
                response = client.get(url, params={"limit": limit, "offset": offset})
                response.raise_for_status()
                payload = response.json()
                rows.extend(parser(payload))

                metadata = payload.get("MRData", {})
                total = self._parse_int(metadata.get("total")) or len(rows)
                returned_limit = self._parse_int(metadata.get("limit")) or limit
                offset += returned_limit
                if offset >= total or returned_limit <= 0:
                    break

        return rows

    def _parse_race(self, race: Dict[str, Any]) -> Optional[F1Race]:
        circuit = race.get("Circuit") or {}
        location = circuit.get("Location") or {}
        race_date = self._parse_date(race.get("date"))

        try:
            season = int(race.get("season"))
            round_number = int(race.get("round"))
        except (TypeError, ValueError):
            return None

        return F1Race(
            season=season,
            round=round_number,
            race_name=str(race.get("raceName") or ""),
            circuit_name=str(circuit.get("circuitName") or ""),
            locality=location.get("locality"),
            country=location.get("country"),
            date=race_date,
            time=race.get("time"),
            raw=race,
        )

    def _parse_race_results(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        race_table = payload.get("MRData", {}).get("RaceTable", {})
        rows: List[Dict[str, Any]] = []
        for race in race_table.get("Races") or []:
            for result in race.get("Results") or []:
                driver = result.get("Driver") or {}
                constructor = result.get("Constructor") or {}
                fastest_lap = result.get("FastestLap") or {}
                rows.append({
                    "season": self._parse_int(race.get("season")),
                    "round": self._parse_int(race.get("round")),
                    "race_name": race.get("raceName"),
                    "driver_id": driver.get("driverId"),
                    "driver_code": driver.get("code"),
                    "driver_number": driver.get("permanentNumber"),
                    "given_name": driver.get("givenName"),
                    "family_name": driver.get("familyName"),
                    "constructor_id": constructor.get("constructorId"),
                    "constructor_name": constructor.get("name"),
                    "grid": self._parse_int(result.get("grid")),
                    "position": self._parse_int(result.get("position")),
                    "position_text": result.get("positionText"),
                    "position_order": self._parse_int(result.get("positionOrder")) or self._parse_int(result.get("position")),
                    "points": self._parse_float(result.get("points")),
                    "laps": self._parse_int(result.get("laps")),
                    "status": result.get("status"),
                    "race_time": (result.get("Time") or {}).get("time"),
                    "fastest_lap_rank": self._parse_int(fastest_lap.get("rank")),
                    "fastest_lap_time": (fastest_lap.get("Time") or {}).get("time"),
                    "source_payload": result,
                })
        return [row for row in rows if row["season"] is not None and row["round"] is not None and row["driver_id"]]

    def _parse_qualifying_results(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        race_table = payload.get("MRData", {}).get("RaceTable", {})
        rows: List[Dict[str, Any]] = []
        for race in race_table.get("Races") or []:
            for result in race.get("QualifyingResults") or []:
                driver = result.get("Driver") or {}
                constructor = result.get("Constructor") or {}
                rows.append({
                    "season": self._parse_int(race.get("season")),
                    "round": self._parse_int(race.get("round")),
                    "race_name": race.get("raceName"),
                    "driver_id": driver.get("driverId"),
                    "driver_code": driver.get("code"),
                    "driver_number": driver.get("permanentNumber"),
                    "given_name": driver.get("givenName"),
                    "family_name": driver.get("familyName"),
                    "constructor_id": constructor.get("constructorId"),
                    "constructor_name": constructor.get("name"),
                    "qualifying_position": self._parse_int(result.get("position")),
                    "q1": result.get("Q1"),
                    "q2": result.get("Q2"),
                    "q3": result.get("Q3"),
                    "source_payload": result,
                })
        return [row for row in rows if row["season"] is not None and row["round"] is not None and row["driver_id"]]

    def _parse_date(self, value: Any) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    def _parse_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
