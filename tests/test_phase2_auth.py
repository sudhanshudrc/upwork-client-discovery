from fastapi.testclient import TestClient
from app.main import app
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


def test_api_auth_login_validation():
    """Verify POST /api/v1/auth/login validates input schemas."""
    # Test valid payload
    payload = {
        "username": "test_user@example.com",
        "password": "valid_secure_password",
        "remember_session": True,
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_authenticated" in data
    assert "rate_limit_health" in data

    # Test invalid short password (< 6 chars)
    invalid_payload = {
        "username": "test_user",
        "password": "123",
    }
    invalid_resp = client.post("/api/v1/auth/login", json=invalid_payload)
    assert invalid_resp.status_code == 422


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

