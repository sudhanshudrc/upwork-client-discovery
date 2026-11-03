import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import get_current_user, get_optional_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.session import AsyncSessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import SessionStatusResponse
from app.schemas.user import AuthTokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import auth_service

logger = logging.getLogger("app.api.v1.auth")

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])


# Helper functions
async def _build_user_response(db_session, user: User) -> UserResponse:
    """Helper to populate UserResponse with user's private Upwork cookie metadata."""
    has_session = False
    cookie_count = 0
    rate_health = "GREEN"

    try:
        stmt = select(UserSession).filter(
            (UserSession.user_id == user.id) | (UserSession.user_identifier == user.email)
        )
        res = await db_session.execute(stmt)
        sess = res.scalars().first()
        if sess:
            has_session = sess.cookie_count > 0
            cookie_count = sess.cookie_count
            rate_health = sess.rate_limit_health or "GREEN"
    except Exception as e:
        logger.warning(f"Could not load UserSession metadata for user {user.email}: {e}")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        has_upwork_session=has_session,
        upwork_cookie_count=cookie_count,
        rate_limit_health=rate_health,
    )


# 1. Application Tenant Account (SaaS Identity)
@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Application Account",
    description="Creates a new tenant user profile with email and password, returning an HS256 JWT access token.",
)
@router.post(
    "/user/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_user(request: UserRegisterRequest):
    """
    Registers a new tenant user account with email and password.
    Hashes the password with PBKDF2-HMAC-SHA256 and returns a signed JWT access token.
    """
    clean_email = request.email.lower().strip()

    async with AsyncSessionLocal() as db_session:
        stmt = select(User).filter_by(email=clean_email)
        res = await db_session.execute(stmt)
        existing = res.scalars().first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{clean_email}' already exists. Please sign in.",
            )

        hashed_pw = hash_password(request.password)
        new_user = User(
            email=clean_email,
            password_hash=hashed_pw,
            full_name=request.full_name.strip() if request.full_name else None,
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()
        await db_session.refresh(new_user)

        user_resp = await _build_user_response(db_session, new_user)

    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
    logger.info(f"[AUTH USER] User registered successfully: {clean_email} ({new_user.id})")

    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="User Account Login",
    description="Authenticates application credentials (email and password) and issues a signed JWT Bearer token.",
)
@router.post(
    "/user/login",
    response_model=AuthTokenResponse,
    include_in_schema=False,
)
async def login_user(request: UserLoginRequest):
    """
    Authenticates a user by email and password, returning a signed JWT access token.
    """
    clean_email = request.email.lower().strip()

    async with AsyncSessionLocal() as db_session:
        stmt = select(User).filter_by(email=clean_email)
        res = await db_session.execute(stmt)
        user = res.scalars().first()

        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been deactivated.",
            )

        user_resp = await _build_user_response(db_session, user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    logger.info(f"[AUTH USER] User logged in successfully: {clean_email} ({user.id})")

    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current User Profile & Status",
    description="Returns the authenticated tenant's user profile, registration timestamp, and Upwork cookie count.",
)
@router.get(
    "/user/me",
    response_model=UserResponse,
    include_in_schema=False,
)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile and Upwork cookie connection status.
    """
    async with AsyncSessionLocal() as db_session:
        return await _build_user_response(db_session, current_user)


# 2. Upwork Cookie Vault & Health Probes
class SessionImportRequest(BaseModel):
    user_identifier: str = Field(default="default", min_length=2, description="Target username or email for this session")
    session_data: Any = Field(..., description="Playwright storage state JSON or cookies list")
    password: Optional[str] = Field(default=None, description="Password to decrypt encrypted Cookie-Editor files")


@router.post(
    "/session/import",
    response_model=SessionStatusResponse,
    summary="Import Upwork Cookies",
    description="Accepts Playwright JSON, encrypted Cookie-Editor files, or raw cookie strings, encrypts with AES-256-GCM, and stores under the logged-in user.",
)
async def import_session_cookies(
    request: SessionImportRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Directly imports session cookies / storage state for a user.
    Persists AES-256-GCM encrypted state to PostgreSQL.
    Enforces tenant identity when authenticated: ignores external user_identifier
    to prevent cross-user session tampering.
    """
    eff_user = current_user.email if current_user else (request.user_identifier or "default")
    user_id = current_user.id if current_user else None
    try:
        result = await auth_service.save_user_session_state_async(
            user_identifier=eff_user,
            state_data=request.session_data,
            user_id=user_id,
            password=request.password,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import session cookies: {str(e)}",
        )


@router.get(
    "/session/status",
    response_model=SessionStatusResponse,
    summary="Upwork Cookie Session Status",
    description="Checks whether the authenticated user has active cookies and returns rate-limit health without navigating.",
)
@router.get(
    "/status",
    response_model=SessionStatusResponse,
    include_in_schema=False,
)
async def get_session_status(
    user_identifier: Optional[str] = Query(None, description="Optional user identifier for unauthenticated fallback sessions"),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns the current session status and cookie metadata from encrypted DB or file
    without triggering a live network navigation.
    When authenticated, strictly enforces caller identity and isolates tenant state.
    """
    if current_user:
        eff_user = current_user.email
        user_id = current_user.id
    else:
        eff_user = user_identifier or "default"
        user_id = None
    return await auth_service.get_session_status_async(user_identifier=eff_user, user_id=user_id)


@router.post(
    "/session/verify",
    response_model=SessionStatusResponse,
    summary="Upwork Connection Liveness Probe",
    description="Launches a headless Playwright probe against Upwork search to test if cookies are active or blocked.",
)
@router.post(
    "/verify",
    response_model=SessionStatusResponse,
    include_in_schema=False,
)
async def verify_session_liveness(
    user_identifier: Optional[str] = Query(None, description="Optional user identifier for unauthenticated fallback sessions"),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Executes a live Playwright probe to verify that stored cookies
    can access Upwork search without Cloudflare challenges or login redirects.
    When authenticated, strictly uses the authenticated user's cookies.
    """
    eff_user = current_user.email if current_user else (user_identifier or "default")
    health = await auth_service.verify_session_health(headless=True, user_identifier=eff_user)
    return health
