import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.search_run import SearchRun
    from app.models.intelligence import ClientIntelligence
    from app.models.candidate import Candidate


class Job(Base):
    """Job Entity: Stores job specs, financial budget, proposal competition, and raw text."""

    __tablename__ = "jobs"

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("search_runs.id", ondelete="SET NULL"), nullable=True
    )

    job_uid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    job_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    pay_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'Hourly' | 'Fixed-price'

    budget_min_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    budget_max_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    project_duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hours_per_week: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    proposals_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    interviewing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invites_sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unanswered_invites: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    skills_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="jobs")
    search_run: Mapped[Optional["SearchRun"]] = relationship(
        "SearchRun", back_populates="jobs"
    )
    intelligence: Mapped[Optional["ClientIntelligence"]] = relationship(
        "ClientIntelligence",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Candidate.rank_order",
    )

    __table_args__ = (
        Index("idx_jobs_uid", "job_uid"),
        Index("idx_jobs_pay", "pay_type", "budget_max_usd"),
        Index("idx_jobs_posted", "posted_at"),
    )

