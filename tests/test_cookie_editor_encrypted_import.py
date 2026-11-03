"""
Integration and unit tests for HotCleaner Cookie-Editor encrypted export imports.
Tests automated decryption using user-provided password and raw unencrypted imports.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models.base import Base
from app.services.auth_service import auth_service

client = TestClient(app)


@pytest.mark.anyio
async def test_cookie_editor_encrypted_import_success(monkeypatch):
    """Verify that encrypted Cookie-Editor payload with correct password decrypts and stores session."""
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.core.deps.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.api.v1.auth.AsyncSessionLocal", async_session)

    with open("cookies.json", "r", encoding="utf-8") as f:
        encrypted_payload = json.load(f)

    # 1. Test direct service normalization
    parsed = auth_service._parse_session_payload(encrypted_payload, password="Drc@1234")
    assert "cookies" in parsed
    assert len(parsed["cookies"]) == 71
    assert any(c.get("domain") == "auth.upwork.com" for c in parsed["cookies"])

    # Verify all sameSite attributes conform to Playwright's strict enum
    for c in parsed["cookies"]:
        assert c["sameSite"] in ("Strict", "Lax", "None"), f"Invalid sameSite: {c['sameSite']}"

    # 2. Test via API endpoint
    email = "cookie_test_user@example.com"
    pwd = "SecureTestPassword123!"
    reg_res = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Post encrypted payload with password
    import_res = client.post(
        "/api/v1/auth/session/import",
        json={
            "user_identifier": email,
            "session_data": encrypted_payload,
            "password": "Drc@1234",
        },
        headers=headers,
    )
    assert import_res.status_code == 200
    data = import_res.json()
    assert data["is_authenticated"] is True
    assert "71 cookies" in data["message"]

    # Verify session status reflects the 71 decrypted cookies
    status_res = client.get("/api/v1/auth/session/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["is_authenticated"] is True
    assert "71 cookies" in status_data["message"]


@pytest.mark.anyio
async def test_cookie_editor_encrypted_import_wrong_password():
    """Verify that an incorrect password or missing password fails with a clear error."""
    with open("cookies.json", "r", encoding="utf-8") as f:
        encrypted_payload = json.load(f)

    # Missing password
    with pytest.raises(ValueError, match="encrypted with a password"):
        auth_service._parse_session_payload(encrypted_payload, password=None)

    # Wrong password
    with pytest.raises(ValueError, match="Could not decrypt"):
        auth_service._parse_session_payload(encrypted_payload, password="WrongPassword999")
