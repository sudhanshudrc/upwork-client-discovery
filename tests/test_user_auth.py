import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.main import app
from app.models.base import Base

client = TestClient(app)


def test_password_hashing_and_verification():
    """Verify PBKDF2-HMAC-SHA256 password hashing and constant-time verification."""
    password = "SuperSecretPassword123"
    hashed = hash_password(password)

    assert hashed.startswith("pbkdf2_sha256$600000$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False


def test_jwt_access_token_creation_and_decoding():
    """Verify HS256 JWT access token generation, payload decoding, and expiration."""
    payload_data = {"sub": "user_uuid_1234", "email": "test@example.com"}
    token = create_access_token(payload_data, expires_delta=timedelta(hours=1))

    decoded = decode_access_token(token)
    assert decoded["sub"] == "user_uuid_1234"
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded

    # Test expired token
    expired_token = create_access_token(payload_data, expires_delta=timedelta(seconds=-10))
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(expired_token)

    # Test tampered token
    tampered = token[:-4] + "abcd"
    with pytest.raises(ValueError, match="signature"):
        decode_access_token(tampered)


@pytest.mark.anyio
async def test_user_registration_and_login_flow(monkeypatch):
    """
    Verifies end-to-end API registration, duplicate detection, login,
    and authenticated profile access using an isolated SQLite in-memory test database.
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkeypatch AsyncSessionLocal across modules
    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.core.deps.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.api.v1.auth.AsyncSessionLocal", async_session)

    # 1. Register new user
    reg_payload = {
        "email": "testuser@agency.io",
        "password": "Password123!",
        "full_name": "Test Agency User",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "testuser@agency.io"
    assert data["user"]["full_name"] == "Test Agency User"
    token = data["access_token"]

    # 2. Duplicate registration attempt should return 409 Conflict
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 3. Weak password should be rejected (< 8 characters)
    weak_res = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@test.com", "password": "short"},
    )
    assert weak_res.status_code == 422

    # 4. Login with correct credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@agency.io", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "testuser@agency.io"

    # 5. Login with invalid password
    bad_login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@agency.io", "password": "WrongPassword!"},
    )
    assert bad_login_res.status_code == 401

    # 6. Authenticated /me endpoint with valid Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "testuser@agency.io"
    assert me_data["full_name"] == "Test Agency User"

    # 7. Unauthenticated /me request should be rejected (401)
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    await engine.dispose()
