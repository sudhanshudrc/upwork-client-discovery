import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClientBase(BaseModel):
    """Base schema with shared client attributes."""

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    local_time: Optional[str] = None
    total_spent_usd: Decimal = Field(default=Decimal("0.00"))
    avg_hourly_rate_usd: Optional[Decimal] = None
    hire_rate_pct: Optional[Decimal] = None
    total_hires: int = 0
    active_hires: int = 0
    client_rating: Optional[Decimal] = None
    total_reviews: int = 0
    payment_verified: bool = True
    company_size: Optional[str] = None
    industry: Optional[str] = None
    member_since: Optional[str] = None


class ClientCreate(ClientBase):
    """Schema for registering or upserting a client."""

    client_uid: Optional[str] = None


class ClientResponse(ClientBase):
    """API Response schema for a client."""

    id: uuid.UUID
    client_uid: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

