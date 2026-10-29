from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.contract import ClientContract


class Client(Base):
    """Client Master Entity: Stores location, verified payment, spending power, and hire stats."""

    __tablename__ = "clients"

    client_uid: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    local_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    total_spent_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    avg_hourly_rate_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    hire_rate_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    total_hires: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_hires: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    client_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_verified: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    member_since: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="client", cascade="all, delete-orphan"
    )
    contracts: Mapped[List["ClientContract"]] = relationship(
        "ClientContract",
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="ClientContract.contract_index",
    )

    __table_args__ = (
        Index("idx_clients_location", "country", "city"),
        Index("idx_clients_spend", "total_spent_usd"),
    )

