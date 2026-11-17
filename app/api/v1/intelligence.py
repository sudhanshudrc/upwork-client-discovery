from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.session import get_db_session
from app.schemas.intelligence import (
    ClientIntelligenceResponse,
    IntelligenceExtractionResponse,
    UserConfirmationRequest,
)
from app.services.nlp_service import nlp_service


router = APIRouter(prefix="/intelligence", tags=["Intelligence & Human-in-the-Loop"])


@router.get("/{job_uid}", response_model=IntelligenceExtractionResponse)
async def extract_job_intelligence(
    job_uid: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Runs the spaCy NLP entity extraction and linguistic pattern mining on the job description
    and partitioned client history reviews, returning suggested client and company names for user review.
    """
    stmt = (
        select(Job)
        .filter_by(job_uid=job_uid)
        .options(
            selectinload(Job.client),
            selectinload(Job.intelligence),
        )
    )
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_uid} not found. Please scrape/expand the job first.",
        )

    # Load contracts for client
    from app.models.contract import ClientContract
    contract_stmt = select(ClientContract).filter_by(client_id=job.client_id)
    c_res = await db.execute(contract_stmt)
    contracts = c_res.scalars().all()
    contract_dicts = [c.to_dict() for c in contracts]
    past_titles = [c.past_title for c in contracts if c.past_title]

    response = await nlp_service.analyze_job_intelligence(
        job_id=job.id,
        job_uid=job.job_uid,
        job_description=job.description,
        contracts=contract_dicts,
        past_titles=past_titles,
        session=db,
    )
    return response


@router.post("/confirm", response_model=ClientIntelligenceResponse)
async def confirm_client_and_organization(
    confirmation: UserConfirmationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Human-in-the-Loop Checkpoint: Confirms or overrides the suggested client person name
    and organization name, persisting changes to PostgreSQL.
    """
    job = None
    if confirmation.job_id:
        res = await db.execute(select(Job).filter_by(id=confirmation.job_id))
        job = res.scalars().first()
    if not job and confirmation.job_uid:
        res = await db.execute(select(Job).filter_by(job_uid=confirmation.job_uid))
        job = res.scalars().first()

    # If job is not in DB yet (e.g. from feed search only), auto-expand/persist it
    if not job and confirmation.job_uid:
        from app.models.search_run import SearchRun
        from app.services.scraper_service import scraper_service

        runs_res = await db.execute(
            select(SearchRun).where(SearchRun.status == "COMPLETED").order_by(SearchRun.created_at.desc())
        )
        runs = runs_res.scalars().all()
        target_raw = None
        for r in runs:
            if r.raw_jobs_payload:
                for j in r.raw_jobs_payload:
                    if isinstance(j, dict) and j.get("uid") == confirmation.job_uid:
                        target_raw = j
                        break
            if target_raw:
                break

        job_url = target_raw.get("url") if target_raw else f"https://www.upwork.com/jobs/~02{confirmation.job_uid}"
        await scraper_service.scrape_job_details(job_url, expand_all_history=False, session=db)
        job_res = await db.execute(select(Job).filter_by(job_uid=confirmation.job_uid))
        job = job_res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found for job_id={confirmation.job_id} or job_uid={confirmation.job_uid}.",
        )

    confirmation.job_id = job.id
    db_intel = await nlp_service.confirm_intelligence(confirmation, session=db)
    return db_intel

