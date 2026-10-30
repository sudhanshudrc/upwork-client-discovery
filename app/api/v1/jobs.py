from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.client import Client
from app.models.search_run import SearchRun
from app.models.session import get_db_session
from app.schemas.job import JobDetailResponse, JobSearchQuery
from app.schemas.dashboard import (
    DashboardClientItem,
    DashboardStatsResponse,
    DiscoveredCandidateSummary,
    HarvestedJobItem,
    JobDomainItem,
    JobDomainJobsResponse,
    OriginJobSummary,
)
from app.services.scraper_service import scraper_service
from app.services.geo_resolver_service import geo_resolver
from app.services.auth_service import auth_service


router = APIRouter(prefix="/jobs", tags=["Jobs & Feed Scraping"])


@router.post("/search")
async def search_job_feed(
    query_body: JobSearchQuery,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Searches Upwork job feed for keywords (e.g. 'automation', 'ai ml'),
    extracts the top jobs, saves Stage 1 snapshot JSON, and registers SearchRun in PostgreSQL.
    """
    try:
        result = await scraper_service.search_feed(
            query=query_body.query,
            limit=query_body.limit,
            force_live=query_body.force_live,
            session=db,
            user_identifier=query_body.user_identifier,
        )
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_uid}/expand")
async def expand_job_details_and_history(
    job_uid: str,
    job_url: str = Query(..., description="Canonical Upwork job URL"),
    force_live: bool = Query(False, description="Bypass local snapshot cache"),
    user_identifier: Optional[str] = Query(None, description="Optional user identifier for multi-tenant sessions"),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Deep-scrapes a specific Upwork job page, dynamically expands 30+ history contracts
    via Playwright DOM pagination, partitions reviews strictly prior to 'To freelancer:',
    saves Stage 2 JSON snapshot, and syncs into PostgreSQL.
    """
    parsed = await scraper_service.scrape_job_details(
        job_url=job_url,
        expand_all_history=True,
        force_live=force_live,
        session=db,
        user_identifier=user_identifier,
    )
    client_info = parsed.get("client", {})
    return {
        "status": "EXPANDED_SUCCESSFULLY",
        "job_uid": job_uid,
        "job_url": job_url,
        "title": parsed["title"],
        "description": parsed.get("description"),
        "pay_type": parsed.get("pay_type"),
        "experience_level": parsed.get("experience_level"),
        "project_duration": parsed.get("project_duration"),
        "proposals_tier": parsed.get("proposals_tier"),
        "interviewing_count": parsed.get("interviewing_count", 0),
        "invites_sent_count": parsed.get("invites_sent_count", 0),
        "skills_tags": parsed.get("skills_tags"),
        "client_city": client_info.get("city"),
        "client_country": client_info.get("country"),
        "client_local_time": client_info.get("local_time"),
        "client_total_spent": str(client_info.get("total_spent_usd")) if client_info.get("total_spent_usd") is not None else "0.00",
        "client_total_hires": client_info.get("total_hires", 0),
        "client_active_hires": client_info.get("active_hires", 0),
        "client_avg_hourly_rate": str(client_info.get("avg_hourly_rate_usd")) if client_info.get("avg_hourly_rate_usd") else None,
        "client_rating": str(client_info.get("client_rating")) if client_info.get("client_rating") else "5.0",
        "client_payment_verified": client_info.get("payment_verified", True),
        "client_company_size": client_info.get("company_size"),
        "client_industry": client_info.get("industry"),
        "client_member_since": client_info.get("member_since"),
        "total_contracts_extracted": len(parsed["contracts"]),
        "in_progress_count": len([c for c in parsed["contracts"] if c["contract_status"] == "In progress"]),
        "completed_count": len([c for c in parsed["contracts"] if c["contract_status"] == "Completed"]),
        "snapshot_path": f"data/snapshots/stage2_jobs/{job_uid}_detailed.json",
    }


@router.get("/domains", response_model=List[JobDomainItem])
async def list_job_domains(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns all distinct search query domains executed throughout the platform,
    ordered chronologically with real-time 1-hour cache state and expiration countdown.
    """
    stmt = (
        select(SearchRun)
        .where(SearchRun.status == "COMPLETED")
        .order_by(SearchRun.created_at.desc())
    )
    res = await db.execute(stmt)
    all_runs = res.scalars().all()

    now_utc = datetime.now(timezone.utc)
    domain_map: Dict[str, Dict[str, Any]] = {}

    for run in all_runs:
        q_key = run.search_query.strip().lower()
        if q_key not in domain_map:
            created_utc = run.created_at
            if created_utc and created_utc.tzinfo is None:
                created_utc = created_utc.replace(tzinfo=timezone.utc)

            age_seconds = (now_utc - created_utc).total_seconds() if created_utc else 99999
            is_active = age_seconds < 3600
            expires_seconds = max(0, int(3600 - age_seconds)) if is_active else 0

            domain_map[q_key] = {
                "query": run.search_query,
                "latest_run_id": str(run.id),
                "latest_run_at": created_utc or now_utc,
                "total_jobs_found": run.total_jobs_found,
                "total_runs_count": 1,
                "is_cache_active": is_active,
                "expires_in_seconds": expires_seconds,
                "expires_in_minutes": int(expires_seconds // 60),
            }
        else:
            domain_map[q_key]["total_runs_count"] += 1

    return [JobDomainItem(**v) for v in domain_map.values()]


@router.get("/domains/{query}/jobs", response_model=JobDomainJobsResponse)
async def get_domain_jobs(
    query: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves all extracted jobs for a specific search query keyword from PostgreSQL.
    """
    clean_query = query.strip()
    stmt = (
        select(SearchRun)
        .where(
            func.lower(SearchRun.search_query) == clean_query.lower(),
            SearchRun.status == "COMPLETED",
        )
        .order_by(SearchRun.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    run = res.scalars().first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No search run found for query domain '{clean_query}'.",
        )

    now_utc = datetime.now(timezone.utc)
    created_utc = run.created_at
    if created_utc and created_utc.tzinfo is None:
        created_utc = created_utc.replace(tzinfo=timezone.utc)
    age_seconds = (now_utc - created_utc).total_seconds() if created_utc else 99999
    is_active = age_seconds < 3600

    return JobDomainJobsResponse(
        query=run.search_query,
        run_id=str(run.id),
        created_at=created_utc,
        total_jobs=run.total_jobs_found,
        is_cache_active=is_active,
        jobs=run.raw_jobs_payload or [],
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns consolidated 4-factor metrics for the dashboard cockpit.
    """
    # 1. Total unique harvested jobs count
    job_uids_query = select(Job.job_uid)
    job_uids_res = await db.execute(job_uids_query)
    unique_uids = set(job_uids_res.scalars().all())

    # Add unexpanded UIDs from SearchRuns
    runs_res = await db.execute(select(SearchRun.raw_jobs_payload).where(SearchRun.status == "COMPLETED"))
    for payload in runs_res.scalars().all():
        if payload and isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("uid"):
                    unique_uids.add(item["uid"])

    harvested_jobs_count = len(unique_uids)

    # 2. Total unique query domains executed
    domains_res = await db.execute(select(func.lower(SearchRun.search_query)).distinct())
    unique_domains = set(domains_res.scalars().all())
    unique_domains_count = len(unique_domains)

    # 3. Potential clients count
    client_count_stmt = select(func.count(Client.id))
    client_count = (await db.execute(client_count_stmt)).scalar() or 0

    # 4. Rate limit health from auth session
    summary = auth_service.get_session_summary()
    is_present = summary.get("exists", False)
    cookie_count = summary.get("cookie_count", 0)

    return DashboardStatsResponse(
        harvested_jobs_count=harvested_jobs_count,
        unique_domains_count=unique_domains_count,
        potential_clients_count=client_count,
        rate_limit_health="GREEN" if is_present else "YELLOW",
        rate_limit_requests_remaining=48 if is_present else 0,
        active_session_cookies=cookie_count,
    )


@router.get("/dashboard/clients", response_model=List[DashboardClientItem])
async def list_dashboard_clients(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns all potential clients with mined intelligence, origin job,
    financial metrics, and discovered candidate profiles with direct LinkedIn queries.
    """
    stmt = (
        select(Job)
        .options(
            selectinload(Job.client),
            selectinload(Job.intelligence),
            selectinload(Job.candidates),
        )
        .order_by(Job.created_at.desc())
    )
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    clients_list: List[DashboardClientItem] = []

    for job in jobs:
        if not job.client:
            continue

        cname = "Client"
        company = None
        role = "CTO"

        if job.intelligence:
            cname = (
                getattr(job.intelligence, "confirmed_client_name", None)
                or getattr(job.intelligence, "suggested_client_name", None)
                or "Client"
            )
            company = (
                getattr(job.intelligence, "confirmed_company_name", None)
                or getattr(job.intelligence, "suggested_company_name", None)
            )
            role = getattr(job.intelligence, "target_role", "CTO") or "CTO"

        city = job.client.city
        country = job.client.country
        loc_str = f"{city}, {country}" if city and country else (country or "Worldwide")

        # Discover candidates
        cand_summaries = [
            DiscoveredCandidateSummary(
                id=str(cand.id),
                rank_order=cand.rank_order,
                full_name=cand.full_name,
                headline=cand.headline,
                linkedin_url=cand.linkedin_url,
                match_score=float(cand.match_score),
                tier=cand.tier,
                profile_location=cand.profile_location,
                scoring_reasons=cand.scoring_reasons if isinstance(cand.scoring_reasons, list) else [],
            )
            for cand in sorted(job.candidates, key=lambda c: c.rank_order)
        ]

        tier_a = next((c for c in cand_summaries if c.match_score >= 70.0 or "Tier A" in c.tier), None)

        # Generate in-app LinkedIn & Google X-Ray search query URLs
        variants = geo_resolver.generate_search_variants(
            client_name=cname,
            city=city,
            country=country,
        )
        direct_search_urls = [v["url"] for v in variants]

        origin_job = OriginJobSummary(
            id=str(job.id),
            job_uid=job.job_uid,
            title=job.title,
            job_url=job.job_url,
            posted_at=job.posted_at,
        )

        clients_list.append(
            DashboardClientItem(
                client_id=str(job.client.id),
                client_name=cname,
                company_name=company,
                target_role=role,
                origin_job=origin_job,
                location=loc_str,
                total_spent_usd=float(job.client.total_spent_usd or 0),
                client_rating=str(job.client.client_rating or "5.0"),
                total_hires=job.client.total_hires or 0,
                active_hires=job.client.active_hires or 0,
                discovered_candidates_count=len(cand_summaries),
                tier_a_candidate=tier_a,
                candidates=cand_summaries,
                direct_search_urls=direct_search_urls,
            )
        )

    return clients_list


@router.get("/all", response_model=List[HarvestedJobItem])
async def list_all_harvested_jobs(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns all harvested jobs saved in PostgreSQL (both Stage 1 feed records and Stage 2 expanded records).
    """
    stmt = (
        select(Job)
        .options(
            selectinload(Job.client),
            selectinload(Job.intelligence),
        )
        .order_by(Job.created_at.desc())
    )
    res = await db.execute(stmt)
    db_jobs = res.scalars().all()

    seen_uids = set()
    harvested_list: List[HarvestedJobItem] = []

    for j in db_jobs:
        seen_uids.add(j.job_uid)
        loc = None
        spent = 0.0
        if j.client:
            loc = f"{j.client.city}, {j.client.country}" if j.client.city and j.client.country else j.client.country
            spent = float(j.client.total_spent_usd or 0)
        cname = j.intelligence.confirmed_client_name if j.intelligence else None

        harvested_list.append(
            HarvestedJobItem(
                id=str(j.id),
                job_uid=j.job_uid,
                title=j.title,
                job_url=j.job_url,
                pay_type=j.pay_type,
                budget_min_usd=float(j.budget_min_usd) if j.budget_min_usd else None,
                budget_max_usd=float(j.budget_max_usd) if j.budget_max_usd else None,
                skills_tags=j.skills_tags,
                is_expanded=True,
                posted_at=j.posted_at,
                created_at=j.created_at,
                client_location=loc,
                client_total_spent=spent,
                client_name=cname,
            )
        )

    # Also include unexpanded jobs from SearchRuns
    runs_stmt = (
        select(SearchRun)
        .where(SearchRun.status == "COMPLETED")
        .order_by(SearchRun.created_at.desc())
    )
    runs_res = await db.execute(runs_stmt)
    for run in runs_res.scalars().all():
        if run.raw_jobs_payload:
            for item in run.raw_jobs_payload:
                uid = item.get("uid")
                if uid and uid not in seen_uids:
                    seen_uids.add(uid)
                    harvested_list.append(
                        HarvestedJobItem(
                            id=f"feed_{uid}",
                            job_uid=uid,
                            title=item.get("title", "Untitled Job"),
                            job_url=item.get("url") or f"https://www.upwork.com/jobs/~02{uid}",
                            pay_type=item.get("pay_type") or "Fixed-price",
                            budget_min_usd=None,
                            budget_max_usd=None,
                            skills_tags=item.get("skills_tags") or "",
                            is_expanded=False,
                            posted_at=None,
                            created_at=run.created_at,
                            client_location=item.get("client_location") or item.get("client_location_snippet") or item.get("location"),
                            client_total_spent=0.0,
                            client_name=None,
                        )
                    )

    return harvested_list


@router.get("/{job_uid}", response_model=JobDetailResponse)
async def get_job_by_uid(
    job_uid: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves full job details, client profile, and all partitioned history contracts from the database.
    """
    stmt = (
        select(Job)
        .filter_by(job_uid=job_uid)
        .options(
            selectinload(Job.client).selectinload(Client.contracts),
            selectinload(Job.candidates),
            selectinload(Job.intelligence),
        )
    )
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_uid} not found in database. Run /{job_uid}/expand first.",
        )
    return job

