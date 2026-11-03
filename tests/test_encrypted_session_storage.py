import asyncio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.security import encrypt_session_data, decrypt_session_data, get_encryption_key
from app.models.base import Base
from app.models.user_session import UserSession
from app.services.auth_service import auth_service
from playwright.async_api import async_playwright


@pytest.fixture
def sample_storage_payload():
    return {
        "cookies": [
            {
                "name": "oauth2_global_js_token",
                "value": "jwt_header.jwt_payload.jwt_signature",
                "domain": "www.upwork.com",
                "path": "/",
                "expires": 1893456000.0,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "master_access_token",
                "value": "sec_token_987654321",
                "domain": ".upwork.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax",
            },
        ],
        "origins": [
            {
                "origin": "https://www.upwork.com",
                "localStorage": [
                    {"name": "user_theme", "value": "dark"}
                ],
            }
        ],
    }


def test_encryption_and_decryption_roundtrip(sample_storage_payload):
    """Verifies that AES-256-GCM encrypts storage state into an authenticated ciphertext and cleanly decrypts it."""
    ciphertext = encrypt_session_data(sample_storage_payload)
    assert isinstance(ciphertext, str)
    # Ensure sensitive credentials do not leak in raw ciphertext
    assert "jwt_header" not in ciphertext
    assert "sec_token_987654321" not in ciphertext

    decrypted = decrypt_session_data(ciphertext)
    assert decrypted == sample_storage_payload
    assert len(decrypted["cookies"]) == 2
    assert decrypted["cookies"][0]["name"] == "oauth2_global_js_token"


@pytest.mark.anyio
async def test_database_user_session_persistence(sample_storage_payload, monkeypatch):
    """
    Verifies that UserSession persists encrypted data to the database
    and can decrypt back to the original dictionary without writing plaintext to disk.
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkeypatch AsyncSessionLocal in auth_service and user_session
    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)

    test_user = "test_encrypted_client_user"

    # Save session via async auth service
    resp = await auth_service.save_user_session_state_async(
        user_identifier=test_user,
        state_data=sample_storage_payload,
    )
    assert resp.is_authenticated is True
    assert resp.rate_limit_health == "GREEN"

    # Verify directly from DB that ciphertext is encrypted and metadata is populated
    async with async_session() as session:
        res = await session.execute(select(UserSession).filter_by(user_identifier=test_user))
        record = res.scalars().first()
        assert record is not None
        assert record.user_identifier == test_user
        assert record.cookie_count == 2
        assert record.has_oauth_token is True
        assert record.token_expires_at is not None
        assert "jwt_header" not in record.encrypted_state

        decrypted_state = record.get_decrypted_state()
        assert decrypted_state["cookies"][0]["name"] == "oauth2_global_js_token"

    # Verify retrieval via get_decrypted_storage_state
    retrieved_state = await auth_service.get_decrypted_storage_state(user_identifier=test_user)
    assert retrieved_state is not None
    assert len(retrieved_state["cookies"]) == 2

    # Verify status via get_session_status_async
    status_resp = await auth_service.get_session_status_async(user_identifier=test_user)
    assert status_resp.is_authenticated is True
    assert "Active encrypted DB session" in status_resp.message

    # Verify list via list_user_sessions_async
    all_sessions = await auth_service.list_user_sessions_async()
    matching = [s for s in all_sessions if s["user_identifier"] == test_user]
    assert len(matching) == 1
    assert matching[0]["storage_type"] == "POSTGRESQL_ENCRYPTED"

    await engine.dispose()


@pytest.mark.anyio
async def test_in_memory_playwright_context_injection(sample_storage_payload, monkeypatch):
    """
    Verifies that create_authenticated_context injects decrypted storage state directly
    from database into Chromium RAM without requiring on-disk state.
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)

    test_user = "test_playwright_in_memory_user"

    # Save to encrypted DB
    await auth_service.save_user_session_state_async(
        user_identifier=test_user,
        state_data=sample_storage_payload,
    )

    async with async_playwright() as p:
        context = await auth_service.create_authenticated_context(
            p,
            user_identifier=test_user,
            headless=True,
        )
        assert context is not None
        cookies = await context.cookies()
        # Verify cookies are injected into Playwright context
        assert len(cookies) >= 1
        cookie_names = [c["name"] for c in cookies]
        assert "oauth2_global_js_token" in cookie_names
        await context.close()

    await engine.dispose()
