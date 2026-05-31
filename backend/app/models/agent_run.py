from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

class RunStatusEnum(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

class AgentRunBase(BaseModel):
    markets_scanned: int = 0
    candidates_evaluated: int = 0
    recommendations_published: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    status: RunStatusEnum

class AgentRunCreate(AgentRunBase):
    pass

class AgentRun(AgentRunBase):
    id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Performance Snapshot Model
class PerformanceSnapshot(BaseModel):
    id: UUID
    snapshot_at: datetime
    total_predictions: int
    correct: int
    incorrect: int
    pending: int
    accuracy_rate: float
    average_edge: float

    class Config:
        from_attributes = True
