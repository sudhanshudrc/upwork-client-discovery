from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserRegisterRequest(BaseModel):
    """Payload for registering a new tenant user account."""

    email: str = Field(..., pattern=EMAIL_REGEX, description="Unique email address for user login")
    password: str = Field(..., min_length=8, description="Secure password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="Optional full name or organization")


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""

    email: str = Field(..., pattern=EMAIL_REGEX, description="Registered account email")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    """Public representation of an authenticated application user."""

    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    has_upwork_session: bool = False
    upwork_cookie_count: int = 0
    rate_limit_health: str = "GREEN"

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    """Authentication response payload containing JWT access token and user profile."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
