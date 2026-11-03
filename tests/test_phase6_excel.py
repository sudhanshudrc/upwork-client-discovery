from decimal import Decimal
from pathlib import Path
import pytest
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.candidate import Candidate
from app.models.client import Client
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.models.search_run import SearchRun
from app.models.session import get_db_session
from app.services.excel_export_service import (
    COLUMNS_SPEC,
    ExcelExportService,
    excel_export_service,
    format_client_name,
    generate_sales_pitch_hook,
)


def test_sales_pitch_hook_generation():
    """Verify dynamic opening pitch hook creation for multiple intelligence levels."""
    # Full intelligence (Name + Company + Tech Stack)
    hook1 = generate_sales_pitch_hook(
        client_name="Yaniv",
        company_name="Tilt",
        job_title="Senior Full Stack Developer",
        skills_tags="Python, React, FastAPI",
    )
    assert "Hi Yaniv" in hook1
    assert "Tilt" in hook1
    assert "Python, React, FastAPI" in hook1

    # Client name only (no company)
    hook2 = generate_sales_pitch_hook(
        client_name="Sarah",
        company_name=None,
        job_title="Lead AI Engineer",
        skills_tags="LangChain, PyTorch",
    )
    assert "Hi Sarah" in hook2
    assert "LangChain, PyTorch" in hook2

    # Generic fallback
    hook3 = generate_sales_pitch_hook(
        client_name=None,
        company_name=None,
        job_title="DevOps Specialist",
        skills_tags=None,
    )
    assert "Hi, I saw your DevOps Specialist posting" in hook3


def test_format_client_name_multi_and_single():
    """Verify format_client_name returns JSON list for multiple names and string for single."""
    intel_none = None
    assert format_client_name(intel_none) == ""

    intel_single = ClientIntelligence(
        confirmed_client_name="Yaniv",
    )
    assert format_client_name(intel_single) == "Yaniv"

    intel_multi = ClientIntelligence(
        confirmed_client_name="Yaniv, Sarah",
    )
    assert format_client_name(intel_multi) == '["Yaniv", "Sarah"]'

    intel_json_multi = ClientIntelligence(
        confirmed_client_name='["Alice", "Bob"]',
    )
    assert format_client_name(intel_json_multi) == '["Alice", "Bob"]'


def test_generate_leads_workbook_structure_and_styling(tmp_path: Path):
    """Verify Master Excel export renders strictly 34 columns, raw URLs, and single row per job."""
    client = Client(
        city="Winnipeg",
        country="Canada",
        total_spent_usd=Decimal("157000.00"),
        hire_rate_pct=Decimal("78.50"),
        total_hires=42,
        active_hires=8,
        avg_hourly_rate_usd=Decimal("55.00"),
        client_rating=Decimal("4.95"),
        total_reviews=50,
        payment_verified=True,
        local_time="04:45 AM CDT",
        member_since="Apr 2017",
    )

    job = Job(
        client_id=client.id,
        job_uid="2114892483288309550",
        job_url="https://www.upwork.com/jobs/~022114892483288309550",
        title="Senior Full Stack Developer",
        pay_type="Hourly",
        budget_min_usd=Decimal("45.00"),
        budget_max_usd=Decimal("75.00"),
        project_duration="3 to 6 months",
        experience_level="Expert",
        hours_per_week="30+ hrs/week",
        proposals_tier="5 to 10",
        interviewing_count=2,
        invites_sent_count=5,
        unanswered_invites=1,
        skills_tags="Python, FastAPI, React",
        description="Developing scalable Tilt web application.",
    )
    job.client = client

    intel = ClientIntelligence(
        job_id=job.id,
        confirmed_client_name="Yaniv, Sarah",
        confirmed_company_name="Tilt",
        target_role="CTO",
        name_confidence=Decimal("95.00"),
        name_mentions_count=12,
        name_evidence_snippet="Yaniv and Sarah were fantastic to work with.",
        company_evidence_snippet="Tilt platform development.",
        is_agency=False,
    )
    job.intelligence = intel

    out_file = tmp_path / "test_leads.xlsx"
    saved_path = excel_export_service.generate_leads_workbook(
        jobs=[job],
        output_path=out_file,
        only_primary=False,
    )

    assert Path(saved_path).exists()

    wb = openpyxl.load_workbook(saved_path)
    ws = wb.active

    # Check Total Columns: strictly 34
    assert len(COLUMNS_SPEC) == 34
    assert ws.max_column == 34

    # Row 1: Title
    assert "Upwork Job Leads" in ws.cell(1, 1).value
    # Row 2: Subtitle
    assert "Total Jobs Exported: 1" in ws.cell(2, 1).value

    # Row 3: Column Headers
    assert ws.cell(3, 1).value == "Job Title"
    assert ws.cell(3, 2).value == "Job URL"
    assert ws.cell(3, 13).value == "hours_per_week"
    assert ws.cell(3, 14).value == "Client Local Time"
    assert ws.cell(3, 15).value == "Payment Verified"
    assert ws.cell(3, 16).value == "Client Rating"
    assert ws.cell(3, 18).value == "Total Spent ($)"
    assert ws.cell(3, 25).value == "Timezone / Local Time"
    assert ws.cell(3, 27).value == "Client Name"
    assert ws.cell(3, 34).value == "Full Job Description"

    # Data Rows: Exactly 1 row per job (Row 4)
    assert ws.max_row == 4

    # Verify Data
    assert ws.cell(4, 1).value == "Senior Full Stack Developer"
    assert ws.cell(4, 13).value == "30+ hrs/week"
    assert ws.cell(4, 15).value == "TRUE"
    assert "$" in ws.cell(4, 18).value  # Total Spent
    assert "%" in ws.cell(4, 19).value  # Hire Rate
    assert ws.cell(4, 27).value == '["Yaniv", "Sarah"]'  # Multi-name formatted as JSON list
    assert ws.cell(4, 31).value == "Tilt"
    assert ws.cell(4, 34).value == "Developing scalable Tilt web application."

    # Verify Raw URL cells have hyperlinks
    job_url_cell = ws.cell(4, 2)
    assert job_url_cell.value.startswith("https://www.upwork.com")
    assert job_url_cell.hyperlink.target.startswith("https://www.upwork.com")


@pytest.mark.anyio
async def test_export_from_db_with_filters(tmp_path: Path):
    """Verify export_from_db executes dynamic queries by min_spend and country."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Job 1: Canada, $157K spend
        c1 = Client(city="Winnipeg", country="Canada", total_spent_usd=Decimal("157000.00"))
        session.add(c1)
        await session.flush()

        j1 = Job(
            client_id=c1.id,
            job_uid="job_can_001",
            job_url="https://www.upwork.com/jobs/~01",
            title="Senior Backend Engineer",
            pay_type="Hourly",
            description="Build scalable APIs.",
        )
        session.add(j1)
        await session.flush()

        # Job 2: US, $5K spend
        c2 = Client(city="Austin", country="United States", total_spent_usd=Decimal("5000.00"))
        session.add(c2)
        await session.flush()

        j2 = Job(
            client_id=c2.id,
            job_uid="job_us_002",
            job_url="https://www.upwork.com/jobs/~02",
            title="Junior Script Writer",
            pay_type="Fixed-price",
            description="Write basic scripts.",
        )
        session.add(j2)
        await session.commit()

        # Test 1: Filter by min_spend >= $50,000 (should match only Canada job)
        out1 = tmp_path / "spend_filter.xlsx"
        await excel_export_service.export_from_db(
            session=session,
            min_spend=Decimal("50000.00"),
            output_path=out1,
        )
        wb1 = openpyxl.load_workbook(out1)
        # Row 1-3 headers, Row 4 data (only 1 row)
        assert wb1.active.max_row == 4
        assert wb1.active.cell(4, 1).value == "Senior Backend Engineer"

        # Test 2: Filter by country "United States"
        out2 = tmp_path / "country_filter.xlsx"
        await excel_export_service.export_from_db(
            session=session,
            country="United States",
            output_path=out2,
        )
        wb2 = openpyxl.load_workbook(out2)
        assert wb2.active.max_row == 4
        assert wb2.active.cell(4, 1).value == "Junior Script Writer"


@pytest.mark.anyio
async def test_api_export_endpoints(tmp_path: Path):
    """Verify FastAPI GET /api/v1/leads/export and /api/v1/leads/{job_uid}/export endpoints."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    async with session_factory() as session:
        client = Client(city="Winnipeg", country="Canada", total_spent_usd=Decimal("157000.00"))
        session.add(client)
        await session.flush()

        job = Job(
            client_id=client.id,
            job_uid="2114892483288309550",
            job_url="https://www.upwork.com/jobs/~022114892483288309550",
            title="Senior Full Stack Developer",
            pay_type="Hourly",
            description="Developing Tilt app.",
        )
        session.add(job)
        await session.flush()

        cand = Candidate(
            job_id=job.id,
            rank_order=1,
            full_name="Yaniv B.",
            headline="CTO at Tilt",
            profile_location="Winnipeg, Manitoba, Canada",
            linkedin_url="https://ca.linkedin.com/in/yanivbirenboim",
            match_score=Decimal("96.00"),
            confidence=Decimal("95.00"),
            tier="Tier A",
            is_primary_resolved=True,
        )
        session.add(cand)
        await session.commit()

    try:
        with TestClient(app) as client:
            # 1. Download specific job export
            resp = client.get("/api/v1/leads/2114892483288309550/export")
            assert resp.status_code == 200
            assert "spreadsheetml.sheet" in resp.headers["content-type"]
            assert len(resp.content) > 1000  # Valid binary Excel file

            # 2. Download bulk leads export with filters
            resp_bulk = client.get("/api/v1/leads/export?min_spend=10000")
            assert resp_bulk.status_code == 200
            assert "spreadsheetml.sheet" in resp_bulk.headers["content-type"]
            assert len(resp_bulk.content) > 1000

            # 3. 404 on nonexistent job
            resp_404 = client.get("/api/v1/leads/nonexistent_job_123/export")
            assert resp_404.status_code == 404

            # 4. Download filtered leads export by search query keyword
            resp_query = client.get("/api/v1/leads/export?query=Full%20Stack")
            assert resp_query.status_code == 200
            assert "spreadsheetml.sheet" in resp_query.headers["content-type"]
            assert "leads_full_stack.xlsx" in resp_query.headers.get("content-disposition", "")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_export_from_db_strictly_search_run_jobs_and_metrics(tmp_path: Path):
    """
    Verify that export_from_db bounds output strictly to the active search query/run count
    (e.g., exactly 3 jobs) rather than dumping all historical DB jobs, and that
    budget_min_usd, budget_max_usd, hours_per_week, and client_rating are accurately populated.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Populate 5 historical irrelevant jobs in the database
        for i in range(1, 6):
            c_old = Client(country="Canada", total_spent_usd=Decimal("1000.00"), client_rating=Decimal("4.50"))
            session.add(c_old)
            await session.flush()
            j_old = Job(
                client_id=c_old.id,
                job_uid=f"historical_job_{i}",
                job_url=f"https://www.upwork.com/jobs/~historical_{i}",
                title=f"Old Python Developer Job {i}",
                pay_type="Hourly",
                budget_min_usd=Decimal("20.00"),
                budget_max_usd=Decimal("35.00"),
                hours_per_week="less than 30 hrs/week",
                description="Old job description.",
            )
            session.add(j_old)
        await session.flush()

        # 2. Add 1 expanded job that matches one of the search results
        c_active = Client(
            city="Berlin",
            country="Germany",
            total_spent_usd=Decimal("45000.00"),
            client_rating=Decimal("4.85"),
            payment_verified=True,
        )
        session.add(c_active)
        await session.flush()

        j_expanded = Job(
            client_id=c_active.id,
            job_uid="auto_job_1",
            job_url="https://www.upwork.com/jobs/~02auto_job_1",
            title="Senior Automation Architect",
            pay_type="Hourly",
            budget_min_usd=Decimal("60.00"),
            budget_max_usd=Decimal("90.00"),
            hours_per_week="30+ hrs/week",
            project_duration="3 to 6 months",
            description="Build robust Python automation pipelines.",
        )
        session.add(j_expanded)
        await session.flush()

        # 3. Create a SearchRun for query 'automation' returning exactly 3 jobs
        raw_payload = [
            {
                "uid": "auto_job_1",
                "title": "Senior Automation Architect",
                "url": "https://www.upwork.com/jobs/~02auto_job_1",
                "budget": "Hourly: $60.00 - $90.00",
                "duration": "3 to 6 months",
                "hours_per_week": "30+ hrs/week",
                "client_rating": "4.85",
                "payment_verified": True,
                "client_location": "Germany",
                "client_spent": "$45,000 spent",
                "snippet": "Build robust Python automation pipelines.",
            },
            {
                "uid": "auto_job_2",
                "title": "RPA Workflow Engineer",
                "url": "https://www.upwork.com/jobs/~02auto_job_2",
                "budget": "Hourly: $35.00 - $55.00",
                "duration": "1 to 3 months",
                "hours_per_week": "less than 30 hrs/week",
                "client_rating": "5.0",
                "payment_verified": True,
                "client_location": "United States",
                "client_spent": "$12,000 spent",
                "snippet": "Automate business workflows.",
            },
            {
                "uid": "auto_job_3",
                "title": "Fixed Price Automation Script",
                "url": "https://www.upwork.com/jobs/~02auto_job_3",
                "budget": "$1,500",
                "duration": "Less than 1 month",
                "hours_per_week": None,
                "client_rating": None,
                "payment_verified": False,
                "client_location": "India",
                "client_spent": "$0 spent",
                "snippet": "Quick scraper automation script.",
            },
        ]

        sr = SearchRun(
            search_query="automation",
            target_limit=3,
            total_jobs_found=3,
            status="COMPLETED",
            raw_jobs_payload=raw_payload,
        )
        session.add(sr)
        await session.commit()
        await session.refresh(sr)

        # 4. Perform export_from_db for query 'automation'
        out_excel = tmp_path / "search_run_strict_export.xlsx"
        await excel_export_service.export_from_db(
            session=session,
            query="automation",
            output_path=out_excel,
        )

        assert out_excel.exists()
        wb = openpyxl.load_workbook(out_excel)
        ws = wb.active

        # Header rows: Row 1 (Title), Row 2 (Subtitle), Row 3 (34 Columns)
        # Data rows: Row 4, 5, 6 (Strictly 3 jobs, NOT the 5 historical jobs)
        assert ws.max_row == 6, f"Expected 6 rows (3 headers + 3 data rows), but got {ws.max_row}"

        # Row 4 (auto_job_1 - Expanded DB Job)
        assert ws.cell(4, 1).value == "Senior Automation Architect"
        assert ws.cell(4, 5).value == "$60.00"   # Budget Min
        assert ws.cell(4, 6).value == "$90.00"   # Budget Max
        assert ws.cell(4, 13).value == "30+ hrs/week"  # hours_per_week
        assert ws.cell(4, 15).value == "TRUE"    # Payment Verified
        assert float(ws.cell(4, 16).value) == 4.85  # Client Rating

        # Row 5 (auto_job_2 - Synthetic Job from Raw Payload)
        assert ws.cell(5, 1).value == "RPA Workflow Engineer"
        assert ws.cell(5, 5).value == "$35.00"   # Budget Min
        assert ws.cell(5, 6).value == "$55.00"   # Budget Max
        assert ws.cell(5, 13).value == "less than 30 hrs/week"  # hours_per_week
        assert ws.cell(5, 15).value == "TRUE"    # Payment Verified
        assert float(ws.cell(5, 16).value) == 5.0  # Client Rating

        # Row 6 (auto_job_3 - Fixed Price Synthetic Job)
        assert ws.cell(6, 1).value == "Fixed Price Automation Script"
        assert ws.cell(6, 5).value == "$1,500.00"  # Budget Min
        assert ws.cell(6, 6).value == "$1,500.00"  # Budget Max
        assert ws.cell(6, 15).value == "FALSE"   # Payment Verified False
        assert ws.cell(6, 16).value is None     # No Client Rating

