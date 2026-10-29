import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.client import ClientResponse
from app.schemas.history import ContractHistoryResponse
from app.schemas.intelligence import ClientIntelligenceResponse
from app.schemas.candidate import CandidateResponse


class JobSearchQuery(BaseModel):
    """Query parameters for Upwork feed search."""

    query: str = Field("automation", description="Search keyword query")
    limit: int = Field(15, ge=1, le=50, description="Number of jobs to extract")
    expand_history: bool = Field(True, description="Whether to expand 30+ history contracts")
    force_live: bool = Field(False, description="Bypass local cache and fetch fresh live DOM")
    user_identifier: Optional[str] = Field(None, description="Optional user identifier for multi-tenant sessions")


class JobBase(BaseModel):
    """Base schema for Upwork job postings."""

    job_uid: str
    job_url: str
    title: str
    pay_type: str
    budget_min_usd: Optional[Decimal] = None
    budget_max_usd: Optional[Decimal] = None
    experience_level: Optional[str] = None
    project_duration: Optional[str] = None
    hours_per_week: Optional[str] = None
    proposals_tier: Optional[str] = None
    interviewing_count: int = 0
    invites_sent_count: int = 0
    unanswered_invites: int = 0
    skills_tags: Optional[str] = None
    description: str
    posted_at: Optional[datetime] = None


class JobCreate(JobBase):
    """Schema for inserting a parsed job."""

    client_id: uuid.UUID
    run_id: Optional[uuid.UUID] = None


class JobSummaryResponse(JobBase):
    """Lightweight summary response for feed listings."""

    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobSummaryResponse):
    """Comprehensive job response with associated client, history, intelligence, and candidates."""

    client: Optional[ClientResponse] = None
    contracts: List[ContractHistoryResponse] = Field(default_factory=list)
    intelligence: Optional[ClientIntelligenceResponse] = None
    candidates: List[CandidateResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

