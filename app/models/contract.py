import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.client import Client


class ClientContract(Base):
    """Client Past Contract History: Stores review history with strict 'To freelancer:' partitioning."""

    __tablename__ = "client_contracts"

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    contract_index: Mapped[int] = mapped_column(Integer, nullable=False)
    past_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contract_status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'In progress' | 'Completed'
    freelancer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # '5.0 / 5.0'
    date_and_budget: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # STRICT PARTITIONING RULE: Text strictly PRIOR to "To freelancer:"
    freelancer_review_clean: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Specific client name mined from this single review (if identified)
    client_name_mined: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Isolated client praise directed at the freelancer (strictly after "To freelancer:")
    excluded_client_praise: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    client: Mapped["Client"] = relationship("Client", back_populates="contracts")

    __table_args__ = (
        Index("idx_contracts_client_idx", "client_id", "contract_index"),
        Index("idx_contracts_mined_name", "client_name_mined"),
    )

