import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user_session import UserSession


class User(Base):
    """
    User Entity:
    Represents an authenticated application account with hashed credentials
    and a dedicated encrypted Upwork cookie session vault.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # 1:1 relationship with UserSession
    session: Mapped[Optional["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
    )

