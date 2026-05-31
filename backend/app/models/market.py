from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class MarketBase(BaseModel):
    polymarket_id: str
    question: str
    category: Optional[str] = "General"
    closing_time: datetime

class MarketCreate(MarketBase):
    pass

class Market(MarketBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
