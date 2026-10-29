import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class ClientIntelligence(Base):
    """Mined Client & Organization Intelligence: Stores spaCy and linguistic entities + Human-in-the-Loop confirmations."""

    __tablename__ = "client_intelligence"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    confirmed_client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confirmed_company_name: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )
    target_role: Mapped[str] = mapped_column(
        String(100), default="CTO", nullable=False
    )

    name_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    name_mentions_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name_evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_agency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agency_detection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human-in-the-Loop review status: 'PENDING', 'APPROVED', 'MODIFIED'
    approval_status: Mapped[str] = mapped_column(
        String(30), default="APPROVED", nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="intelligence")

    __table_args__ = (
        Index("idx_intel_job", "job_id"),
        Index("idx_intel_client_name", "confirmed_client_name"),
        Index("idx_intel_company", "confirmed_company_name"),
    )

