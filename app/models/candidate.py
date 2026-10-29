import uuid
from decimal import Decimal
from typing import Any, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class Candidate(Base):
    """Decision-Maker & Potential Candidates: Stores all harvested LinkedIn profiles with match scoring."""

    __tablename__ = "candidates"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    rank_order: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = Top match, 2, 3...
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str] = mapped_column(Text, nullable=False)  # Raw LinkedIn Profile URL

    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    tier: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Tier A', 'Tier B', 'Tier C'

    # Dual Delivery Flag: TRUE for the top resolved match, FALSE for runners-up
    is_primary_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    scoring_reasons: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="candidates")

    __table_args__ = (
        Index("idx_candidates_job_rank", "job_id", "rank_order"),
        Index("idx_candidates_tier", "tier"),
        Index("idx_candidates_primary", "is_primary_resolved"),
    )

