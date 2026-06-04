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

    def _parse_date(self, value: Any) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None
