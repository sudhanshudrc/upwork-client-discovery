from decimal import Decimal
from pathlib import Path
import pytest
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.candidate import Candidate
from app.models.client import Client
from app.models.contract import ClientContract
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.models.session import get_db_session
from app.services.pipeline_service import pipeline_runner


@pytest.mark.anyio
async def test_e2e_single_job_pipeline_execution(tmp_path: Path):
    """
    Complete End-to-End Verification:
    Runs an Upwork job through the entire 5-stage pipeline from HTML fixture to PostgreSQL/SQLite persistence:
    1. DOM Scrape & Strict Partitioning (30+ contracts)
    2. spaCy NLP Entity Mining (Yaniv / Tilt)
    3. LinkedIn Candidate Harvesting & 4-Factor Scoring
    4. Dual Delivery (Tier A Resolved vs Potential)
    5. Database Sync & Snapshot Verification
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    target_url = "https://www.upwork.com/jobs/~022114892483288309550"

    async with session_factory() as session:
        # Run autonomous job pipeline without rate-limiting jitter for fast testing
        result = await pipeline_runner.execute_job_pipeline(
            job_url=target_url,
            session=session,
            auto_confirm=True,
            apply_delay=False,
        )

        assert result["status"] == "COMPLETED"
        assert result["job_uid"] == "2114892483288309550"
        assert result["client_name"] == "Yaniv"
        assert result["total_contracts"] == 50
        assert result["total_candidates"] > 0
        assert result["primary_resolved_name"] == "Yaniv B."
        assert result["primary_resolved_score"] >= 0.85

        # Verify Relational Database Records
        # 1. Job record
        job_stmt = select(Job).filter_by(job_uid="2114892483288309550")
        job = (await session.execute(job_stmt)).scalars().first()
        assert job is not None
        assert "Tilt" in job.description or "developer" in job.description.lower()

        # 2. Client record
        client_stmt = select(Client).filter_by(id=job.client_id)
        client = (await session.execute(client_stmt)).scalars().first()
        assert client is not None
        assert client.city == "Winnipeg"
        assert client.country == "Canada"
        assert client.total_spent_usd == Decimal("157000.00")

        # 3. Partitioned Contract records (50 contracts)
        contracts_stmt = select(ClientContract).filter_by(client_id=client.id)
        contracts = (await session.execute(contracts_stmt)).scalars().all()
        assert len(contracts) == 50

        # Verify strict partitioning on contract #9
        c9 = [c for c in contracts if c.contract_index == 9][0]
        assert "Yaniv" in c9.freelancer_review_clean
        assert "To freelancer:" not in c9.freelancer_review_clean
        assert c9.excluded_client_praise is not None

        # 4. Intelligence record
        intel_stmt = select(ClientIntelligence).filter_by(job_id=job.id)
        intel = (await session.execute(intel_stmt)).scalars().first()
        assert intel is not None
        assert intel.confirmed_client_name == "Yaniv"
        assert intel.name_mentions_count >= 10

        # 5. Candidate records (Dual delivery)
        cands_stmt = select(Candidate).filter_by(job_id=job.id).order_by(Candidate.rank_order)
        cands = (await session.execute(cands_stmt)).scalars().all()
        assert len(cands) >= 2

        # Primary resolved candidate
        prim = cands[0]
        assert prim.is_primary_resolved is True
        assert prim.full_name == "Yaniv B."
        assert "Tier A" in prim.tier

        # Potential runner-up candidate
        pot = cands[1]
        assert pot.is_primary_resolved is False
        assert pot.full_name == "Yaniv Butorov"
        assert "Tier B" in pot.tier


@pytest.mark.anyio
async def test_e2e_fastapi_gateway_routes():
    """Verify FastAPI Gateway Endpoints (/health, job-run, export) end-to-end."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    try:
        with TestClient(app) as test_client:
            # 1. Root Health Check
            resp_health = test_client.get("/health")
            assert resp_health.status_code == 200
            assert resp_health.json()["status"] == "ONLINE"


            # 2. Trigger Autonomous Single Job Pipeline
            payload = {
                "job_url": "https://www.upwork.com/jobs/~022114892483288309550",
                "auto_confirm": True,
                "apply_delay": False,
            }
            resp_run = test_client.post("/api/v1/pipelines/job-run", json=payload)
            assert resp_run.status_code == 200, resp_run.text
            run_data = resp_run.json()
            assert run_data["status"] == "COMPLETED"
            assert run_data["client_name"] == "Yaniv"
            assert run_data["primary_resolved_name"] == "Yaniv B."

            # 3. Export Leads Excel Workbook
            resp_export = test_client.get("/api/v1/leads/2114892483288309550/export")
            assert resp_export.status_code == 200
            assert "spreadsheetml.sheet" in resp_export.headers["content-type"]
            assert len(resp_export.content) > 1000

            # 4. Bulk Export Leads Excel
            resp_bulk = test_client.get("/api/v1/leads/export?min_spend=50000")
            assert resp_bulk.status_code == 200
            assert len(resp_bulk.content) > 1000
    finally:
        app.dependency_overrides.clear()
