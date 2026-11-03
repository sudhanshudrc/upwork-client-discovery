import logging
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.security import decode_access_token
from app.models.session import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger("app.core.deps")

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> User:
    """
    FastAPI dependency that enforces JWT authentication.
    Extracts Bearer token, validates signature and expiration, and returns the User.
    Raises HTTP 401 UNAUTHORIZED if token is missing, invalid, or expired.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        logger.warning(f"[AUTH DEPS] Token decoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user ID in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncSessionLocal() as db_session:
        stmt = select(User).filter_by(id=user_uuid, is_active=True)
        res = await db_session.execute(stmt)
        user = res.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or has been deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[User]:
    """
    Permissive FastAPI dependency that retrieves the current user if a valid Bearer token is passed,
    or returns None without raising an exception if no token is provided.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

