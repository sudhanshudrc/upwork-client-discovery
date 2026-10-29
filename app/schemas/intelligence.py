import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DiscoveredEntityItem(BaseModel):
    """An individual entity candidate discovered by spaCy or regex."""

    name: str
    confidence: Decimal
    source: str
    mention_count: int = 1
    supporting_context: Optional[str] = None


class IntelligenceExtractionResponse(BaseModel):
    """API Response containing candidate client names & organizations for user review."""

    job_id: uuid.UUID
    job_uid: str
    suggested_client_name: Optional[str]
    suggested_company_name: Optional[str]
    suggested_role: str = "CTO"
    client_name_candidates: List[DiscoveredEntityItem] = Field(default_factory=list)
    company_candidates: List[DiscoveredEntityItem] = Field(default_factory=list)
    is_agency: bool = False
    agency_detection_reason: Optional[str] = None
    approval_status: str = "PENDING"


class UserConfirmationRequest(BaseModel):
    """Human-in-the-Loop: User validates, edits, or approves the client and organization name."""

    job_id: uuid.UUID
    confirmed_client_name: str = Field(..., min_length=2, description="Target client person name")
    confirmed_company_name: Optional[str] = Field(None, description="Target company name")
    target_role: str = Field("CTO", description="Target role e.g. CTO, Founder, CEO")


class ClientIntelligenceResponse(BaseModel):
    """API Response representing confirmed intelligence state."""

    id: uuid.UUID
    job_id: uuid.UUID
    confirmed_client_name: str
    confirmed_company_name: Optional[str]
    target_role: str
    name_confidence: Decimal
    name_mentions_count: int
    name_evidence_snippet: Optional[str]
    company_evidence_snippet: Optional[str]
    is_agency: bool
    approval_status: str
    confirmed_at: datetime

    model_config = ConfigDict(from_attributes=True)

