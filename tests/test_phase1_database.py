import uuid
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.base import Base
from app.models.client import Client
from app.models.job import Job
from app.models.contract import ClientContract
from app.models.intelligence import ClientIntelligence
from app.models.candidate import Candidate
from app.models.search_run import SearchRun
from app.schemas.job import JobDetailResponse
from app.schemas.candidate import LeadDiscoveryResultResponse, CandidateResponse


def test_database_schema_ddl():
    """Verify that all 6 relational models compile valid DDL without relationship or syntax errors."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "search_runs",
        "clients",
        "jobs",
        "client_contracts",
        "client_intelligence",
        "candidates",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_models_relationships_and_strict_partitioning():
    """Verify end-to-end relational data insertion, foreign keys, and strict review partitioning."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Search Run
        run = SearchRun(search_query="automation", target_limit=15, total_jobs_found=1)
        session.add(run)

        # 2. Client
        client = Client(
            client_uid="cli_winnipeg_yaniv",
            city="Winnipeg",
            country="Canada",
            total_spent_usd=Decimal("157000.00"),
            client_rating=Decimal("5.00"),
            payment_verified=True,
            total_hires=85,
            active_hires=10,
        )
        session.add(client)
        session.flush()

        # 3. Job
        job = Job(
            client_id=client.id,
            run_id=run.id,
            job_uid="2114892483288309550",
            job_url="https://www.upwork.com/jobs/~022114892483288309550",
            title="Senior Full Stack Developer",
            pay_type="Hourly",
            budget_max_usd=Decimal("80.00"),
            description="We are seeking a senior full stack developer...",
        )
        session.add(job)
        session.flush()

        # 4. Client Contract (Strict Partitioning Check)
        contract = ClientContract(
            client_id=client.id,
            contract_index=1,
            past_title="Jira admin",
            contract_status="Completed",
            freelancer_name="Markus S.",
            rating="5.0 / 5.0",
            date_and_budget="Sep 2026 - Sep 2026 · Fixed-price $30.00",
            # STRICT RULE: Extracted strictly prior to "To freelancer:"
            freelancer_review_clean="It was a great experience working with Yaniv. He communicated clearly...",
            client_name_mined="Yaniv",
            # Safely isolated praise
            excluded_client_praise="To freelancer: Markus S. Rating is 5.0 out of 5. Working with Markus...",
        )
        session.add(contract)

        # 5. Client Intelligence (NLP Output)
        intel = ClientIntelligence(
            job_id=job.id,
            confirmed_client_name="Yaniv",
            confirmed_company_name="Tilt",
            target_role="CTO",
            name_confidence=Decimal("95.00"),
            name_mentions_count=12,
            name_evidence_snippet="It was a great experience working with Yaniv.",
            approval_status="APPROVED",
        )
        session.add(intel)

        # 6. Candidates (Dual Delivery: Resolved + Potential)
        c1 = Candidate(
            job_id=job.id,
            rank_order=1,
            full_name="Yaniv B.",
            headline="CTO at Tilt",
            profile_location="Winnipeg, Manitoba, Canada",
            linkedin_url="https://www.linkedin.com/in/yanivbirenboim",
            match_score=Decimal("82.00"),
            confidence=Decimal("94.50"),
            tier="Tier A (High Confidence Target)",
            is_primary_resolved=True,
            scoring_reasons=["Exact first name match", "City match: Winnipeg"],
        )
        c2 = Candidate(
            job_id=job.id,
            rank_order=2,
            full_name="Yaniv Butorov",
            headline="University of Manitoba Honors Student",
            profile_location="Winnipeg, Manitoba, Canada",
            linkedin_url="https://www.linkedin.com/in/yaniv-butorov-888371217",
            match_score=Decimal("78.20"),
            confidence=Decimal("94.50"),
            tier="Tier B (Potential Match / Review Required)",
            is_primary_resolved=False,
            scoring_reasons=["Name match", "City match", "Student title"],
        )
        session.add_all([c1, c2])
        session.commit()

        # Query back and verify relationships
        saved_job = session.query(Job).filter_by(job_uid="2114892483288309550").first()
        assert saved_job is not None
        assert saved_job.client.city == "Winnipeg"
        assert len(saved_job.client.contracts) == 1
        assert saved_job.client.contracts[0].client_name_mined == "Yaniv"
        assert saved_job.intelligence.confirmed_company_name == "Tilt"
        assert len(saved_job.candidates) == 2

        # Verify Dual Candidate separation
        resolved = [c for c in saved_job.candidates if c.is_primary_resolved]
        potential = [c for c in saved_job.candidates if not c.is_primary_resolved]
        assert len(resolved) == 1
        assert resolved[0].full_name == "Yaniv B."
        assert len(potential) == 1
        assert potential[0].full_name == "Yaniv Butorov"


def test_pydantic_multi_model_serialization():
    """Verify Pydantic V2 schema serialization from ORM attributes."""
    sample_candidate_id = uuid.uuid4()
    sample_job_id = uuid.uuid4()

    c1_response = CandidateResponse(
        id=sample_candidate_id,
        job_id=sample_job_id,
        rank_order=1,
        full_name="Yaniv B.",
        headline="CTO at Tilt",
        profile_location="Winnipeg, Manitoba, Canada",
        linkedin_url="https://www.linkedin.com/in/yanivbirenboim",
        match_score=Decimal("82.00"),
        confidence=Decimal("94.50"),
        tier="Tier A",
        is_primary_resolved=True,
        created_at="2026-10-28T14:00:00Z",
    )

    result_response = LeadDiscoveryResultResponse(
        job_id=sample_job_id,
        job_uid="2114892483288309550",
        client_name="Yaniv",
        location="Winnipeg, Canada",
        resolved_candidate=c1_response,
        potential_candidates=[],
        direct_linkedin_search_urls=[
            "https://www.linkedin.com/search/results/people/?keywords=Yaniv&geoUrn=%5B%2290008587%22%5D"
        ],
    )

    data = result_response.model_dump()
    assert data["client_name"] == "Yaniv"
    assert data["resolved_candidate"]["full_name"] == "Yaniv B."
    assert data["resolved_candidate"]["is_primary_resolved"] is True
