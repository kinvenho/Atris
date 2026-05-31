from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

class SideEnum(str, Enum):
    YES = "YES"
    NO = "NO"

class StatusEnum(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"

class ResultEnum(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"

# Recommendation Evidence Models
class EvidenceBase(BaseModel):
    source_url: str
    summary: str

class EvidenceCreate(EvidenceBase):
    pass

class Evidence(EvidenceBase):
    id: UUID
    recommendation_id: UUID
    retrieved_at: datetime

    class Config:
        from_attributes = True

# Recommendation Models
class RecommendationBase(BaseModel):
    market_id: Optional[UUID] = None
    market_question: str
    side: SideEnum
    market_probability: float
    atris_probability: float
    edge: float
    confidence: float
    reasoning: str
    evidence_summary: str
    status: StatusEnum = StatusEnum.ACTIVE
    result: ResultEnum = ResultEnum.PENDING

class RecommendationCreate(RecommendationBase):
    evidence: List[EvidenceCreate] = Field(default_factory=list)

class Recommendation(RecommendationBase):
    id: UUID
    created_at: datetime
    resolved_at: Optional[datetime] = None
    evidence: Optional[List[Evidence]] = None

    class Config:
        from_attributes = True
