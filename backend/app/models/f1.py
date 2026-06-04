from datetime import date as Date
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class F1SourceKind(str, Enum):
    HISTORICAL = "historical"
    LIVE = "live"
    ANALYSIS = "analysis"
    MARKET = "market"


class F1SourceStatus(str, Enum):
    READY = "ready"
    EVALUATING = "evaluating"
    ROADMAP = "roadmap"


class F1DataSource(BaseModel):
    name: str
    kind: F1SourceKind
    status: F1SourceStatus
    access: str
    role: str
    notes: str
    url: str


class F1Race(BaseModel):
    season: int
    round: int
    race_name: str
    circuit_name: str
    locality: Optional[str] = None
    country: Optional[str] = None
    date: Optional[Date] = None
    time: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class F1SeasonSchedule(BaseModel):
    season: int
    races: List[F1Race]


class F1Session(BaseModel):
    session_key: int
    meeting_key: int
    session_name: str
    session_type: str
    year: int
    country_name: Optional[str] = None
    location: Optional[str] = None
    circuit_short_name: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class F1LiveReadiness(BaseModel):
    historical_first: bool
    preferred_live_path: str
    supabase_storage_policy: str
    live_options: List[F1DataSource]
