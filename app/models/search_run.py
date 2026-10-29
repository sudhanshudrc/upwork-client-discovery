from typing import List, TYPE_CHECKING
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class SearchRun(Base):
    """Tracks Upwork batch search runs (e.g. 'automation', limit 15)."""

    __tablename__ = "search_runs"

    search_query: Mapped[str] = mapped_column(String(100), nullable=False)
    target_limit: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    total_jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="COMPLETED", nullable=False
    )

    # Relationships
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="search_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_search_runs_created", "created_at"),
        Index("idx_search_runs_query", "search_query"),
    )

