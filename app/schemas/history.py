import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ContractHistoryBase(BaseModel):
    """Base schema for a client past contract."""

    contract_index: int
    past_title: Optional[str] = None
    contract_status: str  # 'In progress' | 'Completed'
    freelancer_name: Optional[str] = None
    rating: Optional[str] = None
    date_and_budget: Optional[str] = None

    # STRICT RULE: Extracted strictly prior to "To freelancer:"
    freelancer_review_clean: Optional[str] = Field(
        None, description="Review text strictly prior to 'To freelancer:'"
    )
    client_name_mined: Optional[str] = Field(
        None, description="Client name identified from this specific review"
    )
    excluded_client_praise: Optional[str] = Field(
        None, description="Client feedback praise directed at freelancer (excluded from identity)"
    )


class ContractHistoryCreate(ContractHistoryBase):
    """Schema for inserting a parsed contract."""

    client_id: uuid.UUID


class ContractHistoryResponse(ContractHistoryBase):
    """API Response schema for a contract history entry."""

    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

