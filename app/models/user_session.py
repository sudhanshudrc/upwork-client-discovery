import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import decrypt_session_data
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSession(Base):
    """
    UserSession Entity:
    Persists AES-256-GCM encrypted Playwright storage_state (cookies + localStorage)
    with token expiration metadata, cookie counts, and rate limit health indicators.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=True,
    )
    user_identifier: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    encrypted_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    cookie_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    has_oauth_token: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rate_limit_health: Mapped[str] = mapped_column(
        String(20),
        default="GREEN",
        nullable=False,
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="session",
    )

    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_identifier", "user_identifier"),
        Index("idx_user_sessions_health", "rate_limit_health"),
    )

    def get_decrypted_state(self) -> Dict[str, Any]:
        """Decrypts the AES-256-GCM payload and returns the Playwright storage_state dictionary."""
        return decrypt_session_data(self.encrypted_state)

