import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.base import Base

client = TestClient(app)


@pytest.mark.anyio
async def test_multi_user_cookie_tenant_isolation(monkeypatch):
    """
    Verifies that User A and User B maintain completely isolated Upwork cookie vaults.
    User A cannot access or overwrite User B's cookies, and API status returns only
    the requesting tenant's session state.
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkeypatch across modules
    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.core.deps.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.api.v1.auth.AsyncSessionLocal", async_session)

    # 1. Register User A (Alice)
    alice_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@company.com", "password": "AlicePassword123", "full_name": "Alice Corp"},
    )
    assert alice_reg.status_code == 201
    alice_token = alice_reg.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # 2. Register User B (Bob)
    bob_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@agency.io", "password": "BobPassword456", "full_name": "Bob Agency"},
    )
    assert bob_reg.status_code == 201
    bob_token = bob_reg.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 3. Initially, neither user has active cookies
    alice_me_init = client.get("/api/v1/auth/me", headers=alice_headers)
    assert alice_me_init.status_code == 200
    assert alice_me_init.json()["has_upwork_session"] is False

    bob_me_init = client.get("/api/v1/auth/me", headers=bob_headers)
    assert bob_me_init.status_code == 200
    assert bob_me_init.json()["has_upwork_session"] is False

    # 4. Alice imports 3 cookies for Alice's account
    alice_cookies = [
        {"name": "oauth2_global_js_token", "value": "alice_jwt_token", "domain": ".upwork.com", "path": "/"},
        {"name": "master_access_token", "value": "alice_master_key", "domain": ".upwork.com", "path": "/"},
        {"name": "user_pref", "value": "alice_theme", "domain": ".upwork.com", "path": "/"},
    ]
    alice_import = client.post(
        "/api/v1/auth/session/import",
        json={"session_data": alice_cookies},
        headers=alice_headers,
    )
    assert alice_import.status_code == 200
    assert alice_import.json()["is_authenticated"] is True

    # 5. Bob imports 1 cookie for Bob's account
    bob_cookies = [
        {"name": "oauth2_global_js_token", "value": "bob_jwt_token", "domain": ".upwork.com", "path": "/"},
    ]
    bob_import = client.post(
        "/api/v1/auth/session/import",
        json={"session_data": bob_cookies},
        headers=bob_headers,
    )
    assert bob_import.status_code == 200
    assert bob_import.json()["is_authenticated"] is True

    # 6. Verify Alice's profile reflects 3 cookies
    alice_me_post = client.get("/api/v1/auth/me", headers=alice_headers)
    assert alice_me_post.status_code == 200
    alice_data = alice_me_post.json()
    assert alice_data["has_upwork_session"] is True
    assert alice_data["upwork_cookie_count"] == 3

    # 7. Verify Bob's profile reflects 1 cookie (not 3)
    bob_me_post = client.get("/api/v1/auth/me", headers=bob_headers)
    assert bob_me_post.status_code == 200
    bob_data = bob_me_post.json()
    assert bob_data["has_upwork_session"] is True
    assert bob_data["upwork_cookie_count"] == 1

    # 8. Verify Alice's session status API query reflects Alice's session
    alice_status = client.get("/api/v1/auth/status", headers=alice_headers)
    assert alice_status.status_code == 200
    assert "alice@company.com" in alice_status.json()["message"]
    assert "3 cookies" in alice_status.json()["message"]

    # 9. Verify Bob's session status API query reflects Bob's session
    bob_status = client.get("/api/v1/auth/status", headers=bob_headers)
    assert bob_status.status_code == 200
    assert "bob@agency.io" in bob_status.json()["message"]
    assert "1 cookies" in bob_status.json()["message"]

    # 10. Verify /api/v1/auth/sessions endpoint is deleted (404) to prevent cross-tenant enumeration
    enum_attempt = client.get("/api/v1/auth/sessions", headers=alice_headers)
    assert enum_attempt.status_code == 404

    # 11. Cross-tenant probe prevention: Alice attempts to inspect Bob's session via query param
    # Backend must enforce caller identity and ignore user_identifier query param override
    alice_probe_bob = client.get("/api/v1/auth/session/status?user_identifier=bob@agency.io", headers=alice_headers)
    assert alice_probe_bob.status_code == 200
    assert "alice@company.com" in alice_probe_bob.json()["message"]
    assert "3 cookies" in alice_probe_bob.json()["message"]
    assert "bob@agency.io" not in alice_probe_bob.json()["message"]

    # 12. Cross-tenant tampering prevention: Alice attempts to overwrite Bob's session via import payload
    # Backend must bind import strictly to authenticated caller (Alice)
    alice_hijack_attempt = client.post(
        "/api/v1/auth/session/import",
        json={
            "user_identifier": "bob@agency.io",
            "session_data": [
                {"name": "oauth2_global_js_token", "value": "alice_tamper_1", "domain": ".upwork.com", "path": "/"},
                {"name": "master_access_token", "value": "alice_tamper_2", "domain": ".upwork.com", "path": "/"},
            ],
        },
        headers=alice_headers,
    )
    assert alice_hijack_attempt.status_code == 200

    # Bob's cookies remain untouched (still 1 cookie)
    bob_me_check = client.get("/api/v1/auth/me", headers=bob_headers)
    assert bob_me_check.status_code == 200
    assert bob_me_check.json()["upwork_cookie_count"] == 1

    # Alice's cookies updated to 2
    alice_me_check = client.get("/api/v1/auth/me", headers=alice_headers)
    assert alice_me_check.status_code == 200
    assert alice_me_check.json()["upwork_cookie_count"] == 2

    await engine.dispose()
