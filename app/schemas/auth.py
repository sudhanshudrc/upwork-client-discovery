from typing import Optional
from pydantic import BaseModel, Field


class UpworkCredentialsCreate(BaseModel):
    """Schema for automated login request."""

    username: str = Field(..., description="Upwork login username or email")
    password: str = Field(..., min_length=6, description="Upwork account password")
    security_answer: Optional[str] = Field(None, description="Security question answer or 2FA pin")
    remember_session: bool = Field(True, description="Persist cookies to storage state")


class SessionStatusResponse(BaseModel):
    """Schema representing current Upwork session health."""

    is_authenticated: bool
    session_file_exists: bool
    user_agent: Optional[str] = None
    rate_limit_health: str = "GREEN"  # 'GREEN', 'YELLOW', 'PAUSED'
    message: str = "Session active"

