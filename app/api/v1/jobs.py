from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.session import get_db_session
from app.schemas.job import JobDetailResponse, JobSearchQuery
from app.services.scraper_service import scraper_service


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
            selectinload(Job.client),
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

