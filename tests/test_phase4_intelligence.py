import pytest
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.base import Base
from app.models.job import Job
from app.models.client import Client
from app.services.scraper_service import parse_job_details_html
from app.services.nlp_service import UpworkNLPService, nlp_service
from app.schemas.intelligence import UserConfirmationRequest


def test_extract_client_names_50_contracts():
    """Verify NLP extraction finds Yaniv as the top client name with high consensus and zero false positives."""
    fixture_path = Path("playground/fixtures/jobs/2114892483288309550.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    job_data = parse_job_details_html(html, "https://www.upwork.com/jobs/~022114892483288309550")
    contracts = job_data["contracts"]

    service = UpworkNLPService()
    candidates = service.extract_client_names(contracts)

    assert len(candidates) > 0, "Expected at least one discovered name"
    top = candidates[0]
    assert top.name == "Yaniv"
    assert top.mention_count >= 10
    assert top.confidence >= Decimal("90.00")

    # Verify NLP Service tagged the individual contract record
    assert contracts[8]["client_name_mined"] == "Yaniv"

    # Ensure no freelancer names (like Dejan) were mistaken for client
    extracted_names_lower = {c.name.lower() for c in candidates}
    assert "dejan" not in extracted_names_lower


def test_extract_organization_names():
    """Verify company extraction captures ORG entities and excludes programming tech stacks."""
    service = UpworkNLPService()
    description = (
        "We at Acme Technologies are seeking an experienced developer to modernize "
        "our Tilt application using Python, FastAPI, React, and Jira."
    )
    orgs = service.extract_organization_names(
        job_description=description,
        past_titles=["Tilt Mobile App Redesign"],
        person_names=["Yaniv"],
    )

    org_names_lower = {o.name.lower() for o in orgs}
    assert any("acme" in name for name in org_names_lower) or "tilt" in org_names_lower

    # Ensure programming languages and tools are excluded
    for tech in ["python", "fastapi", "react", "jira"]:
        assert tech not in org_names_lower


def test_agency_detection_rules():
    """Verify detection of agency intermediaries vs direct employers."""
    service = UpworkNLPService()

    agency_text = "We are a digital agency hiring on behalf of our client for a new web platform."
    is_agency, reason = service.detect_agency(agency_text)
    assert is_agency is True
    assert "agency" in reason.lower() or "client" in reason.lower()

    direct_text = "We are building our own in-house SaaS product and need a dedicated developer."
    is_direct, direct_reason = service.detect_agency(direct_text)
    assert is_direct is False


@pytest.mark.anyio
async def test_human_in_the_loop_workflow():
    """Verify Human-in-the-Loop review and confirmation workflow."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Create client & job
        client = Client(city="Winnipeg", country="Canada", total_spent_usd=Decimal("157000.00"))
        session.add(client)
        await session.flush()

        job = Job(
            client_id=client.id,
            job_uid="2114892483288309550",
            job_url="https://www.upwork.com/jobs/~022114892483288309550",
            title="Senior Full Stack Developer",
            pay_type="Hourly",
            description="Seeking developer for Tilt app.",
        )
        session.add(job)
        await session.commit()

        # Step 1: Automated extraction
        sample_contracts = [
            {
                "contract_index": 1,
                "freelancer_name": "Markus S.",
                "freelancer_review_clean": "It was a great experience working with Yaniv.",
            }
        ]
        result = await nlp_service.analyze_job_intelligence(
            job_id=job.id,
            job_uid=job.job_uid,
            job_description=job.description,
            contracts=sample_contracts,
            session=session,
        )
        assert result.suggested_client_name == "Yaniv"
        assert result.approval_status == "PENDING"

        # Step 2: Human confirmation
        confirm_req = UserConfirmationRequest(
            job_id=job.id,
            confirmed_client_name="Yaniv",
            confirmed_company_name="Tilt",
            target_role="CTO",
        )
        confirmed_record = await nlp_service.confirm_intelligence(confirm_req, session=session)
        assert confirmed_record.approval_status == "APPROVED"
        assert confirmed_record.confirmed_client_name == "Yaniv"
        assert confirmed_record.confirmed_company_name == "Tilt"
        assert confirmed_record.target_role == "CTO"

