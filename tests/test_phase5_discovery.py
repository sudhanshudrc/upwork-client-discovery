import json
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.candidate import Candidate
from app.models.client import Client
from app.models.contract import ClientContract
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.models.session import get_db_session
from app.services.geo_resolver_service import LinkedInGeoResolver, geo_resolver
from app.services.harvester_service import PersonCandidate, SerpApiHarvesterService
from app.services.scorer_service import CandidateScorerService, LeadTarget, scorer_service


def test_geourn_resolution_and_inapp_links():
    """Verify GeoURN mapping resolves city, state, and country URNs and constructs in-app URLs."""
    # Test Metro resolution (Winnipeg -> 90008587)
    res_winnipeg = geo_resolver.resolve(city="Winnipeg", country="Canada")
    assert res_winnipeg is not None
    assert res_winnipeg["level"] == "metro"
    assert res_winnipeg["geo_urn"] == "90008587"

    # Test Country resolution (Canada -> 101174742)
    res_canada = geo_resolver.resolve(country="Canada")
    assert res_canada is not None
    assert res_canada["level"] == "country"
    assert res_canada["geo_urn"] == "101174742"

    # Test State resolution (California -> 102095887)
    res_ca = geo_resolver.resolve(state="California")
    assert res_ca is not None
    assert res_ca["level"] == "state"
    assert res_ca["geo_urn"] == "102095887"

    # Test URL generation
    url = geo_resolver.build_inapp_search_url(keywords="Yaniv", geo_urn="90008587")
    assert "https://www.linkedin.com/search/results/people/?" in url
    assert "geoUrn=%5B%2290008587%22%5D" in url or 'geoUrn=["90008587"]' in url or "90008587" in url
    assert "keywords=Yaniv" in url
    assert "origin=FACETED_SEARCH" in url

    # Test search variants generation
    variants = geo_resolver.generate_search_variants(client_name="Yaniv", city="Winnipeg", country="Canada")
    assert len(variants) >= 2
    assert any("Metro/City" in v["strategy"] for v in variants)


def test_serpapi_harvester_caching_and_parsing():
    """Verify SerpApiHarvesterService loads pre-cached results from disk and parses PersonCandidate objects."""
    cache_dir = Path("playground/fixtures/serpapi_cache")
    harvester = SerpApiHarvesterService(cache_dir=cache_dir)

    # Query for Yaniv in Winnipeg is cached
    candidates = harvester.harvest_candidates(name="Yaniv", city="Winnipeg", country="Canada")
    assert len(candidates) > 0

    # Ensure profile URLs are sanitized and canonical LinkedIn URLs
    first_candidate = candidates[0]
    assert isinstance(first_candidate, PersonCandidate)
    assert first_candidate.profile_url.startswith("https://")
    assert "linkedin.com/in/" in first_candidate.profile_url
    assert "?" not in first_candidate.profile_url  # URL params stripped

    # Check top candidate details
    full_names = [c.full_name for c in candidates]
    assert any("Yaniv" in name for name in full_names)


def test_4_factor_scoring_dual_delivery():
    """Verify 4-factor scoring algorithm and dual delivery (Primary Resolved vs Potential Candidates)."""
    scorer = CandidateScorerService()
    target = LeadTarget(
        name="Yaniv",
        city="Winnipeg",
        country="Canada",
        company_hint="Tilt",
        domain_keywords=["Python", "React", "Mobile"],
    )

    candidate_a = PersonCandidate(
        full_name="Yaniv B.",
        headline="CTO at Tilt",
        location_text="Winnipeg, Manitoba, Canada · Executive Leadership",
        profile_url="https://ca.linkedin.com/in/yanivbirenboim",
    )

    candidate_b = PersonCandidate(
        full_name="Yaniv Butorov",
        headline="University of Manitoba Honors Student",
        location_text="Winnipeg, Manitoba, Canada",
        profile_url="https://ca.linkedin.com/in/yaniv-butorov-888371217",
    )

    candidate_c = PersonCandidate(
        full_name="John Doe",
        headline="Software Engineer at Generic Corp",
        location_text="Toronto, Ontario, Canada",
        profile_url="https://ca.linkedin.com/in/johndoe",
    )

    ranked = scorer.rank_and_separate(target, [candidate_b, candidate_c, candidate_a])

    # Rank #1 must be Yaniv B. (CTO at Tilt)
    assert ranked[0].candidate.full_name == "Yaniv B."
    assert ranked[0].is_primary_resolved is True
    assert "Tier A" in ranked[0].tier
    assert ranked[0].score >= 0.85

    # Rank #2 must be Yaniv Butorov (Tier B Potential)
    assert ranked[1].candidate.full_name == "Yaniv Butorov"
    assert ranked[1].is_primary_resolved is False
    assert "Tier B" in ranked[1].tier

    # Rank #3 must be low match Tier C
    assert ranked[2].is_primary_resolved is False
    assert "Tier C" in ranked[2].tier


@pytest.mark.anyio
async def test_database_persistence_and_stage4_snapshot():
    """Verify persisting scored candidates to database and generating Stage 4 JSON snapshot."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
        await session.commit()

        target = LeadTarget(name="Yaniv", city="Winnipeg", country="Canada", company_hint="Tilt")
        c1 = PersonCandidate(
            full_name="Yaniv B.",
            headline="CTO at Tilt",
            location_text="Winnipeg, Canada",
            profile_url="https://ca.linkedin.com/in/yanivbirenboim",
        )
        c2 = PersonCandidate(
            full_name="Yaniv Butorov",
            headline="Student at University of Manitoba",
            location_text="Winnipeg, Canada",
            profile_url="https://ca.linkedin.com/in/yaniv-butorov",
        )

        ranked = scorer_service.rank_and_separate(target, [c1, c2])

        snapshot_payload = await scorer_service.persist_candidates(
            job_id=job.id,
            job_uid=job.job_uid,
            scored_candidates=ranked,
            session=session,
        )

        # Check snapshot contents
        assert snapshot_payload["total_candidates"] == 2
        assert snapshot_payload["resolved_candidate"]["candidate"]["full_name"] == "Yaniv B."
        assert len(snapshot_payload["potential_candidates"]) == 1
        assert snapshot_payload["potential_candidates"][0]["candidate"]["full_name"] == "Yaniv Butorov"

        # Verify disk snapshot file exists
        snapshot_file = Path(f"data/snapshots/stage4_leads/{job.job_uid}_leads.json")
        assert snapshot_file.exists()


@pytest.mark.anyio
async def test_api_lead_discovery_endpoint():
    """Verify POST /api/v1/leads/{job_uid}/discover executes dual candidate delivery and database sync."""
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

        intel = ClientIntelligence(
            job_id=job.id,
            confirmed_client_name="Yaniv",
            confirmed_company_name="Tilt",
            target_role="CTO",
            name_confidence=Decimal("95.00"),
            name_mentions_count=12,
            is_agency=False,
        )
        session.add(intel)
        await session.commit()

    try:
        with TestClient(app) as test_client:
            resp = test_client.post("/api/v1/leads/2114892483288309550/discover")
            assert resp.status_code == 200, resp.text
            data = resp.json()

            assert data["job_uid"] == "2114892483288309550"
            assert data["client_name"] == "Yaniv"
            assert "Winnipeg" in data["location"]

            # Dual Delivery verification
            resolved = data["resolved_candidate"]
            assert resolved is not None
            assert resolved["is_primary_resolved"] is True
            assert "Yaniv" in resolved["full_name"]
            assert "Tier A" in resolved["tier"]

            potential = data["potential_candidates"]
            assert len(potential) > 0
            assert all(p["is_primary_resolved"] is False for p in potential)
            assert any("Yaniv Butorov" in p["full_name"] for p in potential)

            assert len(data["direct_linkedin_search_urls"]) > 0
            assert "/api/v1/leads/2114892483288309550/export" in data["excel_download_url"]
    finally:
        app.dependency_overrides.clear()

