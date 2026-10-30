import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.base import Base
from app.models.client import Client
from app.models.job import Job
from app.models.intelligence import ClientIntelligence
from app.models.candidate import Candidate
from app.models.search_run import SearchRun
from app.models.session import get_db_session


@pytest.fixture
async def dashboard_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    # Seed initial test data
    async with session_factory() as session:
        # 1. Search Run
        run = SearchRun(
            search_query="automation",
            target_limit=10,
            total_jobs_found=2,
            status="COMPLETED",
            raw_jobs_payload=[
                {"uid": "2116001", "title": "CRM Automation Engineer", "pay_type": "Fixed-price", "client_location": "Sydney, Australia"},
                {"uid": "2116002", "title": "Python Lead Architect", "pay_type": "Hourly", "client_location": "London, United Kingdom"},
            ],
            is_cached_hit=False,
        )
        session.add(run)

        # 2. Client & Expanded Job with Intelligence & Candidates
        client = Client(
            city="Sydney",
            country="Australia",
            total_spent_usd=Decimal("1700.00"),
            total_hires=120,
            active_hires=19,
            client_rating=Decimal("5.0"),
            payment_verified=True,
        )
        session.add(client)
        await session.flush()

        job = Job(
            client_id=client.id,
            job_uid="2116001",
            job_url="https://www.upwork.com/jobs/~022116001",
            title="CRM Automation Engineer",
            pay_type="Fixed-price",
            budget_max_usd=Decimal("500.00"),
            description="Looking for CRM automation specialist...",
        )
        session.add(job)
        await session.flush()

        intelligence = ClientIntelligence(
            job_id=job.id,
            confirmed_client_name="Zarina",
            confirmed_company_name="Mobile CRM",
            target_role="CTO",
            is_agency=False,
            approval_status="APPROVED",
        )
        session.add(intelligence)

        candidate = Candidate(
            job_id=job.id,
            rank_order=1,
            full_name="Zarina M.",
            headline="Lead CRM Specialist",
            profile_location="Sydney, Australia",
            linkedin_url="https://www.linkedin.com/in/zarina-m",
            match_score=Decimal("88.50"),
            confidence=Decimal("0.90"),
            tier="Tier A",
            is_primary_resolved=True,
            scoring_reasons=["Name exact match", "Location Sydney match"],
        )
        session.add(candidate)
        await session.commit()

    yield

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_dashboard_stats_endpoint(dashboard_test_db):
    """Verify /jobs/dashboard/stats returns consolidated metrics."""
    client = TestClient(app)
    response = client.get("/api/v1/jobs/dashboard/stats")
    assert response.status_code == 200
    data = response.json()

    assert data["harvested_jobs_count"] >= 2
    assert data["unique_domains_count"] >= 1
    assert data["potential_clients_count"] >= 1
    assert data["rate_limit_health"] in ["GREEN", "YELLOW"]
    assert data["rate_limit_requests_remaining"] > 0


@pytest.mark.anyio
async def test_domains_list_and_jobs_endpoints(dashboard_test_db):
    """Verify /jobs/domains and /jobs/domains/{query}/jobs endpoints."""
    client = TestClient(app)

    # 1. List Domains
    res = client.get("/api/v1/jobs/domains")
    assert res.status_code == 200
    domains = res.json()
    assert len(domains) >= 1
    domain = next(d for d in domains if d["query"] == "automation")
    assert domain["total_jobs_found"] == 2
    assert domain["total_runs_count"] == 1
    assert domain["is_cache_active"] is True
    assert domain["expires_in_seconds"] > 3500

    # 2. Get Domain Jobs
    res_jobs = client.get("/api/v1/jobs/domains/automation/jobs")
    assert res_jobs.status_code == 200
    job_data = res_jobs.json()
    assert job_data["query"] == "automation"
    assert len(job_data["jobs"]) == 2
    assert job_data["jobs"][0]["uid"] == "2116001"

    # 3. Non-existent domain returns 404
    res_404 = client.get("/api/v1/jobs/domains/nonexistentkeyword/jobs")
    assert res_404.status_code == 404


@pytest.mark.anyio
async def test_dashboard_clients_endpoint(dashboard_test_db):
    """Verify /jobs/dashboard/clients returns clients with origin job and candidates."""
    client = TestClient(app)
    res = client.get("/api/v1/jobs/dashboard/clients")
    assert res.status_code == 200
    clients = res.json()
    assert len(clients) >= 1

    c = next(cl for cl in clients if cl["client_name"] == "Zarina")
    assert c["company_name"] == "Mobile CRM"
    assert c["origin_job"]["job_uid"] == "2116001"
    assert "Sydney" in c["location"]
    assert c["total_spent_usd"] == 1700.0
    assert c["discovered_candidates_count"] == 1
    assert c["tier_a_candidate"]["full_name"] == "Zarina M."
    assert len(c["direct_search_urls"]) > 0


@pytest.mark.anyio
async def test_all_harvested_jobs_endpoint(dashboard_test_db):
    """Verify /jobs/all returns all database and feed-cached jobs."""
    client = TestClient(app)
    res = client.get("/api/v1/jobs/all")
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) >= 2

    # Check both expanded and feed items exist
    uids = [j["job_uid"] for j in jobs]
    assert "2116001" in uids
    assert "2116002" in uids

    expanded_job = next(j for j in jobs if j["job_uid"] == "2116001")
    assert expanded_job["is_expanded"] is True
    assert expanded_job["client_name"] == "Zarina"

