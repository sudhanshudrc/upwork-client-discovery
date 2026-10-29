import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateBase(BaseModel):
    """Base schema for a discovered LinkedIn candidate."""

    rank_order: int
    full_name: str
    headline: Optional[str] = None
    profile_location: Optional[str] = None
    linkedin_url: str
    match_score: Decimal
    confidence: Decimal
    tier: str  # 'Tier A', 'Tier B', 'Tier C'
    is_primary_resolved: bool = False
    scoring_reasons: Optional[Any] = None


class CandidateCreate(CandidateBase):
    """Schema for inserting a candidate record."""

    job_id: uuid.UUID


class CandidateResponse(CandidateBase):
    """API Response schema for a candidate."""

    id: uuid.UUID
    job_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadDiscoveryResultResponse(BaseModel):
    """Dual Delivery Response: Primary resolved decision-maker + potential candidates."""

    job_id: uuid.UUID
    job_uid: str
    client_name: str
    location: str
    resolved_candidate: Optional[CandidateResponse]
    potential_candidates: List[CandidateResponse] = Field(default_factory=list)
    direct_linkedin_search_urls: List[str] = Field(default_factory=list)
    search_variants: List[Dict[str, Any]] = Field(default_factory=list)
    excel_download_url: Optional[str] = None

