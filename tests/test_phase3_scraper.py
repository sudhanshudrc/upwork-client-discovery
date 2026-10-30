import pytest
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.base import Base
from app.models.job import Job
from app.models.client import Client
from app.models.contract import ClientContract
from app.services.scraper_service import (
    parse_search_feed_html,
    parse_job_details_html,
    clean_text,
    parse_currency_amount,
    scraper_service,
)
from app.core.rate_limiter import apply_jitter_delay


def test_parse_search_feed_sample():
    """Verify search feed parsing from raw article elements."""
    sample_feed_html = """
    <article data-ev-job-uid="123456789">
        <h2 data-test="job-tile-title-link">Python Automation Engineer</h2>
        <span data-test="job-type-label">Fixed-price $500</span>
        <span data-test="experience-level">Expert</span>
        <p data-test="job-description-text">Looking for an engineer to build FastAPI backends...</p>
        <span data-test="total-spent">$50K+ spent</span>
        <span data-test="client-country">United States</span>
    </article>
    """
    jobs = parse_search_feed_html(sample_feed_html)
    assert len(jobs) == 1
    j = jobs[0]
    assert j["uid"] == "123456789"
    assert j["title"] == "Python Automation Engineer"
    assert "$500" in j["budget"]
    assert j["experience_level"] == "Expert"
    assert j["client_spent_snippet"] == "$50K+ spent"


def test_parse_job_details_50_contracts_strict_partitioning():
    """Verify parsing of job 2114892483288309550 with all 50 contracts and strict review partitioning."""
    fixture_path = Path("playground/fixtures/jobs/2114892483288309550.html")
    assert fixture_path.exists(), "Expanded HTML fixture must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    job_url = "https://www.upwork.com/jobs/~022114892483288309550"
    data = parse_job_details_html(html, job_url)

    # Job level verification
    assert data["job_uid"] == "2114892483288309550"
    assert data["title"] == "Senior Full Stack Developer"
    assert data["client"]["city"] == "Winnipeg"
    assert data["client"]["country"] == "Canada"
    assert data["client"]["total_spent_usd"] == Decimal("157000.00")

    # Contract level verification
    contracts = data["contracts"]
    assert len(contracts) == 50, f"Expected 50 contracts, found {len(contracts)}"

    in_progress = [c for c in contracts if c["contract_status"] == "In progress"]
    completed = [c for c in contracts if c["contract_status"] == "Completed"]
    assert len(in_progress) == 8, f"Expected 8 in progress, found {len(in_progress)}"
    assert len(completed) == 42, f"Expected 42 completed, found {len(completed)}"

    # STRICT PARTITIONING VERIFICATION:
    # 1. No review text should contain "To freelancer:"
    for c in contracts:
        rev = c.get("freelancer_review_clean")
        if rev:
            assert "To freelancer:" not in rev, f"Partition violation in contract #{c['contract_index']}"

    # 2. Verify Contract #9 (Markus S.) has isolated client praise
    c9 = contracts[8]
    assert c9["contract_status"] == "Completed"
    assert c9["freelancer_name"] == "Markus S."
    assert "Yaniv" in c9["freelancer_review_clean"]
    assert c9["excluded_client_praise"] is not None
    assert "To freelancer: Markus S." in c9["excluded_client_praise"]

    # 3. Verify Contract #13 (Dejan D.) where freelancer left no review but client praised freelancer
    c13 = contracts[12]
    assert c13["freelancer_review_clean"] is None
    assert c13["client_name_mined"] is None
    assert "Dejan" in c13["excluded_client_praise"]  # Safely quarantined


@pytest.mark.anyio
async def test_scraper_database_sync():
    """Verify syncing detailed job and contracts to SQLAlchemy async database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    fixture_path = Path("playground/fixtures/jobs/2114892483288309550.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    parsed = parse_job_details_html(html, "https://www.upwork.com/jobs/~022114892483288309550")

    async with session_factory() as session:
        job = await scraper_service.sync_job_to_db(parsed, session)
        assert job.id is not None
        assert job.job_uid == "2114892483288309550"
        assert job.client.city == "Winnipeg"

        # Verify contracts saved
        from sqlalchemy import select
        res = await session.execute(select(ClientContract).filter_by(client_id=job.client_id))
        saved_contracts = res.scalars().all()
        assert len(saved_contracts) == 50


@pytest.mark.anyio
async def test_jitter_rate_limiter():
    """Verify anti-blocking jitter functions with bounded sleep times."""
    t = await apply_jitter_delay(min_seconds=0.01, max_seconds=0.05)
    assert 0.01 <= t <= 0.05


@pytest.mark.anyio
async def test_search_feed_1_hour_database_cache():
    """Verify 1-hour database caching logic on search_runs table."""
    from datetime import datetime, timezone, timedelta
    from app.models.search_run import SearchRun

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    sample_jobs = [
        {"uid": "998877", "title": "CRM Automation Engineer", "budget": "$500"},
        {"uid": "998878", "title": "FastAPI Lead Architect", "budget": "$1200"},
    ]

    async with session_factory() as session:
        # 1. Insert a fresh SearchRun (< 60 minutes ago)
        fresh_run = SearchRun(
            search_query="automation",
            target_limit=15,
            total_jobs_found=len(sample_jobs),
            status="COMPLETED",
            raw_jobs_payload=sample_jobs,
            is_cached_hit=False,
        )
        session.add(fresh_run)
        await session.commit()
        await session.refresh(fresh_run)

        # 2. Query within 1 hour: Must HIT database cache
        cached_result = await scraper_service.search_feed(
            query="automation",
            limit=10,
            force_live=False,
            session=session,
        )
        assert cached_result["is_cached"] is True
        assert cached_result["total_extracted"] == 2
        assert cached_result["jobs"][0]["uid"] == "998877"
        assert cached_result["expires_in_seconds"] > 3500

        # 3. Query case-insensitively ('AuToMaTiOn'): Must also HIT cache
        case_result = await scraper_service.search_feed(
            query="  AuToMaTiOn  ",
            limit=10,
            force_live=False,
            session=session,
        )
        assert case_result["is_cached"] is True
        assert case_result["total_extracted"] == 2

        # 4. Modify run timestamp to simulate > 1 hour expiration
        fresh_run.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        session.add(fresh_run)
        await session.commit()

        # Check expired run directly: search_feed will bypass it because age >= 3600
        # In an environment without Upwork auth, live search raises RuntimeError, confirming cache miss
        with pytest.raises(Exception):
            await scraper_service.search_feed(
                query="automation",
                limit=10,
                force_live=False,
                session=session,
            )


