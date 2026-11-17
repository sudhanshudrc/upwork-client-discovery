import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ScheduledKeywordSearch(Base):
    """Configuration for recurring automated keyword search and email delivery."""

    __tablename__ = "scheduled_keyword_searches"

    user_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    search_keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    target_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Frequency definitions
    frequency_type: Mapped[str] = mapped_column(
        String(20), default="CRON", nullable=False
    )  # 'CRON' | 'INTERVAL'
    execution_time: Mapped[str] = mapped_column(
        String(10), default="10:30", nullable=False
    )
    selected_days: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )  # e.g. ["wed", "thu", "fri", "sat", "sun"]
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Kolkata", nullable=False
    )
    interval_hours: Mapped[Optional[int]] = mapped_column(
        Integer, default=6, nullable=True
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Anti-bot pacing bounds in seconds
    min_delay_seconds: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    max_delay_seconds: Mapped[float] = mapped_column(Float, default=120.0, nullable=False)

    # Email notification recipients and preferences
    recipient_emails: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    email_subject_template: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Lifecycle & status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    execution_logs: Mapped[List["ScheduleExecutionLog"]] = relationship(
        "ScheduleExecutionLog",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="desc(ScheduleExecutionLog.created_at)",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_scheduled_keyword_active", "is_active"),
        Index("idx_scheduled_keyword_next_run", "next_run_at"),
        Index("idx_scheduled_keyword_user", "user_identifier"),
    )


class ScheduleExecutionLog(Base):
    """Historical execution audit log for a scheduled keyword run."""

    __tablename__ = "schedule_execution_logs"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("scheduled_keyword_searches.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False
    )  # 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'
    jobs_scraped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_expanded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    excel_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_status: Mapped[str] = mapped_column(
        String(30), default="SKIPPED", nullable=False
    )  # 'SKIPPED' | 'SENT' | 'FAILED'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    schedule: Mapped["ScheduledKeywordSearch"] = relationship(
        "ScheduledKeywordSearch", back_populates="execution_logs"
    )

    __table_args__ = (
        Index("idx_exec_logs_schedule_id", "schedule_id"),
        Index("idx_exec_logs_status", "status"),
        Index("idx_exec_logs_created", "created_at"),
    )
