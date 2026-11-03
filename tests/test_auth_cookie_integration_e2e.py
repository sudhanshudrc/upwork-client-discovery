import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.base import Base

client = TestClient(app)


@pytest.mark.anyio
async def test_frontend_backend_auth_cookie_lifecycle(monkeypatch):
    """
    Comprehensive End-to-End integration test validating:
    1. Sign up (Register) and Sign In (Login) flows matching the frontend AuthPage.
    2. Password verification and duplicate email protection.
    3. User profile verification (/auth/me).
    4. Red Signal cookie state: Brand new user has 0 cookies and is_authenticated=False.
    5. Cookie provisioning: User A imports cookies, becoming authenticated.
    6. Strict multi-tenant isolation: User B signs up and sees NO cookies from User A.
    7. Persistent vault: User A logs out and logs back in; cookies remain intact.
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkeypatch database session across auth layers
    monkeypatch.setattr("app.models.session.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.core.deps.AsyncSessionLocal", async_session)
    monkeypatch.setattr("app.api.v1.auth.AsyncSessionLocal", async_session)

    # -------------------------------------------------------------
    # Step 1: User A Registration (Sign Up on AuthPage)
    # -------------------------------------------------------------
    user_a_email = "user_a@agency.com"
    user_a_pass = "SecurePass123!"

    reg_res_a = client.post(
        "/api/v1/auth/register",
        json={"email": user_a_email, "password": user_a_pass, "full_name": "User Alpha"},
    )
    assert reg_res_a.status_code == 201, f"User A registration failed: {reg_res_a.text}"
    data_a = reg_res_a.json()
    assert "access_token" in data_a
    token_a = data_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify duplicate email registration is rejected (HTTP 409)
    dup_res = client.post(
        "/api/v1/auth/register",
        json={"email": user_a_email, "password": "AnotherPassword123"},
    )
    assert dup_res.status_code == 409

    # -------------------------------------------------------------
    # Step 2: Sign In Verification (Login on AuthPage)
    # -------------------------------------------------------------
    # Wrong password test
    wrong_pw_res = client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": "WrongPassword999"},
    )
    assert wrong_pw_res.status_code == 401

    # Correct login test
    login_res_a = client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": user_a_pass},
    )
    assert login_res_a.status_code == 200
    assert login_res_a.json()["access_token"] is not None

    # -------------------------------------------------------------
    # Step 3: Check Initial Cookie State for User A (Red Signal in Header)
    # -------------------------------------------------------------
    me_a_init = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_a_init.status_code == 200
    me_a_json = me_a_init.json()
    assert me_a_json["has_upwork_session"] is False
    assert me_a_json["upwork_cookie_count"] == 0

    status_a_init = client.get("/api/v1/auth/status", headers=headers_a)
    assert status_a_init.status_code == 200
    assert status_a_init.json()["is_authenticated"] is False
    # This is_authenticated=False triggers the Red Signal ("Cookies Needed") in the frontend header!

    # -------------------------------------------------------------
    # Step 4: User A imports Upwork cookies (ConnectionPage)
    # -------------------------------------------------------------
    sample_cookies_a = [
        {"name": "oauth2_global_js_token", "value": "token_a_123", "domain": ".upwork.com", "path": "/"},
        {"name": "XSRF-TOKEN", "value": "xsrf_a_456", "domain": ".upwork.com", "path": "/"},
        {"name": "master_access_token", "value": "master_a_789", "domain": ".upwork.com", "path": "/"},
    ]
    import_res_a = client.post(
        "/api/v1/auth/session/import",
        json={"session_data": sample_cookies_a},
        headers=headers_a,
    )
    assert import_res_a.status_code == 200
    assert import_res_a.json()["is_authenticated"] is True

    # User A status now connected (Red Signal turns Green)
    me_a_active = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_a_active.json()["has_upwork_session"] is True
    assert me_a_active.json()["upwork_cookie_count"] == 3

    status_a_active = client.get("/api/v1/auth/status", headers=headers_a)
    assert status_a_active.json()["is_authenticated"] is True
    assert "3 cookies" in status_a_active.json()["message"]

    # -------------------------------------------------------------
    # Step 5: User B registers (Sign Up on a different browser/tenant)
    # -------------------------------------------------------------
    user_b_email = "user_b@enterprise.com"
    user_b_pass = "EnterprisePass456!"

    reg_res_b = client.post(
        "/api/v1/auth/register",
        json={"email": user_b_email, "password": user_b_pass, "full_name": "User Beta"},
    )
    assert reg_res_b.status_code == 201
    token_b = reg_res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # -------------------------------------------------------------
    # Step 6: Verify User B has COMPLETE Cookie Separation (Must Show Red Signal)
    # -------------------------------------------------------------
    me_b = client.get("/api/v1/auth/me", headers=headers_b)
    assert me_b.status_code == 200
    assert me_b.json()["has_upwork_session"] is False
    assert me_b.json()["upwork_cookie_count"] == 0

    status_b = client.get("/api/v1/auth/status", headers=headers_b)
    assert status_b.status_code == 200
    assert status_b.json()["is_authenticated"] is False
    # User B MUST see Red Signal ("Cookies Needed"), completely separated from User A!

    # -------------------------------------------------------------
    # Step 7: User B imports their own independent cookies
    # -------------------------------------------------------------
    sample_cookies_b = [
        {"name": "oauth2_global_js_token", "value": "token_b_999", "domain": ".upwork.com", "path": "/"},
    ]
    import_res_b = client.post(
        "/api/v1/auth/session/import",
        json={"session_data": sample_cookies_b},
        headers=headers_b,
    )
    assert import_res_b.status_code == 200

    # User B now has 1 cookie
    me_b_post = client.get("/api/v1/auth/me", headers=headers_b)
    assert me_b_post.json()["has_upwork_session"] is True
    assert me_b_post.json()["upwork_cookie_count"] == 1

    # User A STILL has 3 cookies intact (no cross-contamination!)
    me_a_recheck = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_a_recheck.json()["has_upwork_session"] is True
    assert me_a_recheck.json()["upwork_cookie_count"] == 3

    # -------------------------------------------------------------
    # Step 8: User A relogin lifecycle test (Logout -> Login)
    # -------------------------------------------------------------
    # Relogin User A
    relogin_a = client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": user_a_pass},
    )
    assert relogin_a.status_code == 200
    new_token_a = relogin_a.json()["access_token"]
    new_headers_a = {"Authorization": f"Bearer {new_token_a}"}

    # Verify User A's cookies are restored seamlessly on relogin
    me_a_relogin = client.get("/api/v1/auth/me", headers=new_headers_a)
    assert me_a_relogin.json()["has_upwork_session"] is True
    assert me_a_relogin.json()["upwork_cookie_count"] == 3

    await engine.dispose()

