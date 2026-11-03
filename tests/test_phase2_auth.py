import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models.base import Base
from app.services.auth_service import UpworkAuthService


client = TestClient(app)


def test_root_health():
    """Verify application root health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "Upwork" in data["project"]


def test_auth_service_session_detection():
    """Verify auth service detects the existing session state file."""
    service = UpworkAuthService()
    assert service.is_session_file_present() is True

    summary = service.get_session_summary()
    assert summary["exists"] is True
    assert summary["cookie_count"] > 0
    assert any("upwork.com" in d for d in summary["domains"])


def test_api_auth_status_endpoint():
    """Verify GET /api/v1/auth/status returns correct schema and active status."""
    response = client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_authenticated"] is True
    assert data["session_file_exists"] is True
    assert data["rate_limit_health"] == "GREEN"
    assert "cookies" in data["message"].lower()


@pytest.mark.anyio
async def test_api_auth_login_validation(monkeypatch):
    """Verify POST /api/v1/auth/login validates input schemas."""
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.api.v1.auth.AsyncSessionLocal", async_session)

    # Test valid schema with unregistered user (returns 401, confirming schema passed)
    payload = {
        "email": "nonexistent_user@example.com",
        "password": "valid_secure_password",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

    # Test invalid email schema
    invalid_payload = {
        "email": "not_an_email",
        "password": "123",
    }
    invalid_resp = client.post("/api/v1/auth/login", json=invalid_payload)
    assert invalid_resp.status_code == 422

    await engine.dispose()


def test_multi_tenant_session_resolution():
    """Verify multi-tenant user isolation resolves separate file paths per user."""
    service = UpworkAuthService()
    alice_path = service.resolve_user_state_path("alice@corp.com")
    bob_path = service.resolve_user_state_path("bob@agency.io")
    default_path = service.resolve_user_state_path()

    assert alice_path.name == "session_alice_corp_com.json"
    assert bob_path.name == "session_bob_agency_io.json"
    assert alice_path != bob_path
    assert default_path.name == "upwork_state.json"


def test_session_import_endpoint():
    """Verify POST /api/v1/auth/session/import accepts JSON and raw string formats."""
    # Test JSON cookies import
    json_payload = {
        "user_identifier": "test_import_user",
        "session_data": [
            {
                "name": "oauth2_global_js_token",
                "value": "token_abc123",
                "domain": ".upwork.com",
                "path": "/",
            }
        ],
    }
    resp = client.post("/api/v1/auth/session/import", json=json_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_authenticated"] is True
    assert data["rate_limit_health"] == "GREEN"

    # Test raw cookie string import
    raw_payload = {
        "user_identifier": "test_raw_user",
        "session_data": "oauth2_global_js_token=token_xyz987; master_access_token=token_master",
    }
    resp_raw = client.post("/api/v1/auth/session/import", json=raw_payload)
    assert resp_raw.status_code == 200
    data_raw = resp_raw.json()
    assert data_raw["is_authenticated"] is True
    assert data_raw["rate_limit_health"] == "GREEN"


