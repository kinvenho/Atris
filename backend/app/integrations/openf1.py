from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models.f1 import F1Session


class OpenF1Client:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.OPENF1_BASE_URL).rstrip("/")

    def fetch_sessions(
        self,
        year: int | None = None,
        country_name: str | None = None,
        session_type: str | None = None,
        limit: int = 100,
    ) -> List[F1Session]:
        params: Dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if country_name:
            params["country_name"] = country_name
        if session_type:
            params["session_type"] = session_type

        url = f"{self.base_url}/sessions"
        with httpx.Client(timeout=settings.F1_HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        sessions = [self._parse_session(item) for item in response.json()]
        return [session for session in sessions if session is not None][:limit]

    def _parse_session(self, item: Dict[str, Any]) -> Optional[F1Session]:
        try:
            session_key = int(item.get("session_key"))
            meeting_key = int(item.get("meeting_key"))
            year = int(item.get("year"))
        except (TypeError, ValueError):
            return None

        return F1Session(
            session_key=session_key,
            meeting_key=meeting_key,
            session_name=str(item.get("session_name") or ""),
            session_type=str(item.get("session_type") or ""),
            year=year,
            country_name=item.get("country_name"),
            location=item.get("location"),
            circuit_short_name=item.get("circuit_short_name"),
            date_start=self._parse_datetime(item.get("date_start")),
            date_end=self._parse_datetime(item.get("date_end")),
            raw=item,
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        clean_value = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_value)
        except ValueError:
            return None
