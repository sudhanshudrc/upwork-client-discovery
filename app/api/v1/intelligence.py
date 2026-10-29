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
    and organization name before initiating LinkedIn discovery searches.
    """
    stmt = select(Job).filter_by(id=confirmation.job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID {confirmation.job_id} not found.",
        )

    db_intel = await nlp_service.confirm_intelligence(confirmation, session=db)
    return db_intel

