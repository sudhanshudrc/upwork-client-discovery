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
from app.models.session import get_db_session
from app.services.excel_export_service import (
    COLUMNS_SPEC,
    ExcelExportService,
    excel_export_service,
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


def test_generate_leads_workbook_structure_and_styling(tmp_path: Path):
    """Verify Master Excel export renders 46 columns, 6 functional zones, raw URLs, and tier styling."""
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
        confirmed_client_name="Yaniv",
        confirmed_company_name="Tilt",
        target_role="CTO",
        name_confidence=Decimal("95.00"),
        name_mentions_count=12,
        name_evidence_snippet="Yaniv was fantastic to work with.",
        company_evidence_snippet="Tilt platform development.",
        is_agency=False,
    )
    job.intelligence = intel

    cand1 = Candidate(
        job_id=job.id,
        rank_order=1,
        full_name="Yaniv B.",
        headline="CTO at Tilt",
        profile_location="Winnipeg, Manitoba, Canada",
        linkedin_url="https://ca.linkedin.com/in/yanivbirenboim",
        match_score=Decimal("96.00"),
        confidence=Decimal("95.00"),
        tier="Tier A (High Confidence Target)",
        is_primary_resolved=True,
    )

    cand2 = Candidate(
        job_id=job.id,
        rank_order=2,
        full_name="Yaniv Butorov",
        headline="University of Manitoba Honors Student",
        profile_location="Winnipeg, Manitoba, Canada",
        linkedin_url="https://ca.linkedin.com/in/yaniv-butorov-888371217",
        match_score=Decimal("74.50"),
        confidence=Decimal("95.00"),
        tier="Tier B (Potential Match / Review Required)",
        is_primary_resolved=False,
    )
    job.candidates = [cand1, cand2]

    out_file = tmp_path / "test_leads.xlsx"
    saved_path = excel_export_service.generate_leads_workbook(
        jobs=[job],
        output_path=out_file,
        only_primary=False,
    )

    assert Path(saved_path).exists()

    # Load workbook and inspect cell contents and styling
    wb = openpyxl.load_workbook(saved_path)
    ws = wb.active

    # Check Total Columns
    assert len(COLUMNS_SPEC) == 46
    assert ws.max_column == 46

    # Row 1: Title
    assert "Master Intelligence Export" in ws.cell(1, 1).value
    # Row 3: Zone Headers
    assert "Zone 1" in str(ws.cell(3, 1).value)
    assert "Zone 2" in str(ws.cell(3, 10).value)
    assert "Zone 3" in str(ws.cell(3, 15).value)
    assert "Zone 4" in str(ws.cell(3, 27).value)
    assert "Zone 5" in str(ws.cell(3, 36).value)
    assert "Zone 6" in str(ws.cell(3, 44).value)

    # Row 4: Column Headers
    assert ws.cell(4, 1).value == "Job Title"
    assert ws.cell(4, 2).value == "Job URL"
    assert ws.cell(4, 36).value == "Decision Maker Name"
    assert ws.cell(4, 40).value == "Match Tier"
    assert ws.cell(4, 41).value == "LinkedIn Profile URL"
    assert ws.cell(4, 46).value == "Recommended Pitch Hook"

    # Data Rows: Row 5 (Cand 1, Tier A) and Row 6 (Cand 2, Tier B)
    assert ws.max_row == 6

    # Verify Cand 1 (Tier A)
    assert ws.cell(5, 36).value == "Yaniv B."
    assert ws.cell(5, 40).value == "Tier A (High Confidence Target)"
    # Tier A background color check
    fill_a = ws.cell(5, 40).fill
    assert fill_a.start_color.rgb in ("00E2EFDA", "E2EFDA")

    # Verify Raw URL cells have hyperlinks and unmasked text
    job_url_cell = ws.cell(5, 2)
    assert job_url_cell.value.startswith("https://www.upwork.com")
    assert job_url_cell.hyperlink.target.startswith("https://www.upwork.com")

    li_url_cell = ws.cell(5, 41)
    assert li_url_cell.value == "https://ca.linkedin.com/in/yanivbirenboim"
    assert li_url_cell.hyperlink.target == "https://ca.linkedin.com/in/yanivbirenboim"

    # Verify In-App Search links
    metro_url_cell = ws.cell(5, 42)
    assert "90008587" in metro_url_cell.value or "Yaniv" in metro_url_cell.value
    assert metro_url_cell.hyperlink is not None

    # Verify Currency & Percentage formatting
    assert "$" in ws.cell(5, 18).value  # Total Spent
    assert "%" in ws.cell(5, 19).value  # Hire Rate
    assert "%" in ws.cell(5, 39).value  # Match Score

    # Verify Cand 2 (Tier B)
    assert ws.cell(6, 36).value == "Yaniv Butorov"
    assert ws.cell(6, 40).value == "Tier B (Potential Match / Review Required)"
    fill_b = ws.cell(6, 40).fill
    assert fill_b.start_color.rgb in ("00FFF2CC", "FFF2CC")


@pytest.mark.anyio
async def test_export_from_db_with_filters(tmp_path: Path):
    """Verify export_from_db executes dynamic queries by min_spend, country, and tier."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Job 1: Canada, $157K spend, Tier A
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

        cand1 = Candidate(
            job_id=j1.id,
            rank_order=1,
            full_name="Alex Mercer",
            headline="Founder",
            linkedin_url="https://linkedin.com/in/alex",
            match_score=Decimal("92.00"),
            confidence=Decimal("90.00"),
            tier="Tier A",
            is_primary_resolved=True,
        )
        session.add(cand1)

        # Job 2: US, $5K spend, Tier C
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
        await session.flush()

        cand2 = Candidate(
            job_id=j2.id,
            rank_order=1,
            full_name="Sam Smith",
            headline="Freelance Writer",
            linkedin_url="https://linkedin.com/in/sam",
            match_score=Decimal("45.00"),
            confidence=Decimal("50.00"),
            tier="Tier C",
            is_primary_resolved=True,
        )
        session.add(cand2)
        await session.commit()

        # Test 1: Filter by min_spend >= $50,000 (should match only Canada job)
        out1 = tmp_path / "spend_filter.xlsx"
        await excel_export_service.export_from_db(
            session=session,
            min_spend=Decimal("50000.00"),
            output_path=out1,
        )
        wb1 = openpyxl.load_workbook(out1)
        # Row 1-4 headers, Row 5 data (only 1 row)
        assert wb1.active.max_row == 5
        assert wb1.active.cell(5, 1).value == "Senior Backend Engineer"

        # Test 2: Filter by country "United States"
        out2 = tmp_path / "country_filter.xlsx"
        await excel_export_service.export_from_db(
            session=session,
            country="United States",
            output_path=out2,
        )
        wb2 = openpyxl.load_workbook(out2)
        assert wb2.active.max_row == 5
        assert wb2.active.cell(5, 1).value == "Junior Script Writer"


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
            resp_bulk = client.get("/api/v1/leads/export?min_spend=10000&tier=Tier%20A")
            assert resp_bulk.status_code == 200
            assert "spreadsheetml.sheet" in resp_bulk.headers["content-type"]
            assert len(resp_bulk.content) > 1000

            # 3. 404 on nonexistent job
            resp_404 = client.get("/api/v1/leads/nonexistent_job_123/export")
            assert resp_404.status_code == 404
    finally:
        app.dependency_overrides.clear()

