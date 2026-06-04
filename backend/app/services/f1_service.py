from datetime import date
from typing import List

from app.integrations.jolpica import JolpicaClient
from app.integrations.openf1 import OpenF1Client
from app.models.f1 import (
    F1DataSource,
    F1LiveReadiness,
    F1Race,
    F1SeasonSchedule,
    F1Session,
    F1SourceKind,
    F1SourceStatus,
)


class F1Service:
    @staticmethod
    def get_sources() -> List[F1DataSource]:
        return [
            F1DataSource(
                name="F1DB",
                kind=F1SourceKind.HISTORICAL,
                status=F1SourceStatus.EVALUATING,
                access="open-source local artifacts",
                role="Historical warehouse seed for seasons, races, drivers, constructors, circuits, results, qualifying, sprint, and standings.",
                notes="Best candidate for compact local historical ingestion without repeatedly calling external APIs.",
                url="https://github.com/f1db/f1db",
            ),
            F1DataSource(
                name="Jolpica-F1",
                kind=F1SourceKind.HISTORICAL,
                status=F1SourceStatus.READY,
                access="public Ergast-compatible API",
                role="Schedules, standings, race results, qualifying, laps, pit stops, sprint results, and status data.",
                notes="Good first API because response sizes are modest and entities are stable.",
                url="https://github.com/jolpica/jolpica-f1",
            ),
            F1DataSource(
                name="FastF1",
                kind=F1SourceKind.ANALYSIS,
                status=F1SourceStatus.EVALUATING,
                access="open-source Python package",
                role="Session loading, timing data, telemetry analysis, and offline feature generation.",
                notes="Use for feature engineering and live timing recording prototypes, not direct Supabase raw telemetry storage.",
                url="https://github.com/theOehrly/Fast-F1",
            ),
            F1DataSource(
                name="OpenF1",
                kind=F1SourceKind.LIVE,
                status=F1SourceStatus.READY,
                access="public historical API; paid real-time access",
                role="Historical and live-style session data: laps, car data, positions, weather, race control, stints, pit, and sessions.",
                notes="Use historical endpoints immediately; evaluate paid real-time only after live ingestion needs are proven.",
                url="https://openf1.org/docs/",
            ),
            F1DataSource(
                name="Formula 1 SignalR live timing via FastF1",
                kind=F1SourceKind.LIVE,
                status=F1SourceStatus.ROADMAP,
                access="server-side live recording prototype",
                role="Potential Atris-owned live race-weekend feed when paid API access is not justified.",
                notes="Record live sessions, normalize event summaries, and keep raw high-frequency data outside Postgres.",
                url="https://docs.fastf1.dev/",
            ),
            F1DataSource(
                name="Polymarket",
                kind=F1SourceKind.MARKET,
                status=F1SourceStatus.READY,
                access="public market APIs",
                role="Market metadata, prices, liquidity, price movement, and edge comparison.",
                notes="Existing Atris integration already fetches Polymarket market candidates.",
                url="https://docs.polymarket.com/",
            ),
        ]

    @staticmethod
    def get_live_readiness() -> F1LiveReadiness:
        live_options = [
            source
            for source in F1Service.get_sources()
            if source.kind == F1SourceKind.LIVE
        ]
        return F1LiveReadiness(
            historical_first=True,
            preferred_live_path="Start with OpenF1 historical/session endpoints, then prototype FastF1 live timing recording during a race weekend.",
            supabase_storage_policy="Store canonical entities, compact feature snapshots, prediction snapshots, and live-event summaries. Keep raw high-frequency telemetry out of Postgres by default.",
            live_options=live_options,
        )

    @staticmethod
    def get_schedule(season: int | str = "current") -> F1SeasonSchedule:
        return JolpicaClient().fetch_schedule(season)

    @staticmethod
    def get_race_results(season: int | str = "current") -> List[dict]:
        return JolpicaClient().fetch_race_results(season)

    @staticmethod
    def get_qualifying_results(season: int | str = "current") -> List[dict]:
        return JolpicaClient().fetch_qualifying_results(season)

    @staticmethod
    def get_upcoming_races(season: int | str = "current", limit: int = 5) -> List[F1Race]:
        schedule = F1Service.get_schedule(season)
        today = date.today()
        upcoming = [
            race for race in schedule.races
            if race.date is not None and race.date >= today
        ]
        return upcoming[:limit]

    @staticmethod
    def get_sessions(
        year: int | None = None,
        country_name: str | None = None,
        session_type: str | None = None,
        limit: int = 100,
    ) -> List[F1Session]:
        return OpenF1Client().fetch_sessions(
            year=year,
            country_name=country_name,
            session_type=session_type,
            limit=limit,
        )
