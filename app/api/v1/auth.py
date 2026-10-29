from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.schemas.auth import SessionStatusResponse, UpworkCredentialsCreate
from app.services.auth_service import auth_service


router = APIRouter(prefix="/auth", tags=["Authentication & Session"])


@router.get("/sessions")
async def list_available_sessions() -> List[Dict[str, Any]]:
    """
    Returns a list of all stored user sessions in the system.
    """
    return auth_service.list_user_sessions()


@router.get("/status", response_model=SessionStatusResponse)
async def get_session_status(
    user_identifier: Optional[str] = Query(None, description="Optional user identifier for multi-tenant sessions"),
):
    """
    Returns the current session file status and cookie metadata
    without triggering a live network navigation.
    """
    summary = auth_service.get_session_summary(user_identifier=user_identifier)
    is_present = summary.get("exists", False)

    return SessionStatusResponse(
        is_authenticated=is_present,
        session_file_exists=is_present,
        user_agent=auth_service.DEFAULT_USER_AGENT,
        rate_limit_health="GREEN" if is_present else "YELLOW",
        message=(
            f"Active session found for '{user_identifier or 'default'}' with {summary.get('cookie_count', 0)} cookies."
            if is_present
            else f"No active session file found for '{user_identifier or 'default'}'. Authentication required."
        ),
    )


@router.post("/verify", response_model=SessionStatusResponse)
async def verify_session_liveness(
    user_identifier: Optional[str] = Query(None, description="Optional user identifier for multi-tenant sessions"),
):
    """
    Executes a live Playwright probe to verify that stored cookies
    can access Upwork search without Cloudflare challenges or login redirects.
    """
    health = await auth_service.verify_session_health(headless=True, user_identifier=user_identifier)
    return health


class SessionImportRequest(BaseModel):
    user_identifier: str = Field(..., min_length=2, description="Target username or email for this session")
    session_data: Any = Field(..., description="Playwright storage state JSON or cookies list")


@router.post("/session/import", response_model=SessionStatusResponse)
async def import_session_cookies(request: SessionImportRequest):
    """
    Directly imports session cookies / storage state for a user.
    Useful for developers on corporate networks with 2FA / Turnstile.
    """
    try:
        result = auth_service.save_user_session_state(
            user_identifier=request.user_identifier,
            state_data=request.session_data,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import session cookies: {str(e)}",
        )


@router.post("/login", response_model=SessionStatusResponse)
async def login_with_credentials(credentials: UpworkCredentialsCreate):
    """
    Initiates an authenticated session workflow.
    Validates provided credentials format and triggers automated Playwright
    login to capture and persist session cookies into an isolated per-user cache.
    """
    if not credentials.username or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required.",
        )

    # Trigger live or cached Playwright authentication per user
    result = await auth_service.login_with_credentials(
        username=credentials.username,
        password=credentials.password,
        user_identifier=credentials.username,
    )
    if not result.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.message,
        )
    return result

