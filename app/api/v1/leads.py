from decimal import Decimal
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.session import get_db_session
from app.schemas.candidate import (
    CandidateResponse,
    LeadDiscoveryResultResponse,
)
from app.services.excel_export_service import excel_export_service
from app.services.geo_resolver_service import geo_resolver
from app.services.harvester_service import harvester_service
from app.services.scorer_service import LeadTarget, scorer_service



router = APIRouter(prefix="/leads", tags=["Leads & Decision-Maker Discovery"])


@router.post("/{job_uid}/discover", response_model=LeadDiscoveryResultResponse)
async def discover_decision_makers(
    job_uid: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Executes the full decision-maker discovery pipeline:
    1. Resolves location to LinkedIn GeoURN and generates in-app search links.
    2. Runs prioritized Google X-Ray searches via SerpAPI.
    3. Scores candidates using 4-factor scoring (Name 40%, Location 35%, Role 15%, Company 10%).
    4. Delivers both the Primary Resolved Candidate (Tier A) and all Potential Candidates (Tier B & C).
    5. Commits candidates to PostgreSQL and writes Stage 4 JSON snapshot.
    """
    stmt = (
        select(Job)
        .filter_by(job_uid=job_uid)
        .options(
            selectinload(Job.client),
            selectinload(Job.intelligence),
            selectinload(Job.candidates),
        )
    )
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_uid} not found. Please scrape/expand the job first.",
        )

    # Client name resolution
    client_name = "Client"
    company_hint = None
    if job.intelligence and job.intelligence.confirmed_client_name:
        client_name = job.intelligence.confirmed_client_name
        company_hint = job.intelligence.confirmed_company_name
    else:
        from app.models.contract import ClientContract
        from app.services.nlp_service import nlp_service
        from app.schemas.intelligence import UserConfirmationRequest

        contract_stmt = select(ClientContract).filter_by(client_id=job.client_id)
        c_res = await db.execute(contract_stmt)
        contracts = c_res.scalars().all()
        if contracts:
            contract_dicts = [c.to_dict() for c in contracts]
            intel_res = await nlp_service.analyze_job_intelligence(
                job_id=job.id,
                job_uid=job.job_uid,
                job_description=job.description,
                contracts=contract_dicts,
                session=db,
            )
            if intel_res.suggested_client_name:
                top_name = intel_res.suggested_client_name
                top_comp = intel_res.suggested_company_name
                confirm_req = UserConfirmationRequest(
                    job_id=job.id,
                    confirmed_client_name=top_name,
                    confirmed_company_name=top_comp,
                    target_role="CTO",
                )
                await nlp_service.confirm_intelligence(confirm_req, db)
                client_name = top_name
                company_hint = top_comp



    city = job.client.city if job.client else None
    country = job.client.country if job.client else None

    # 1. GeoURN Search Variants
    search_variants = geo_resolver.generate_search_variants(
        client_name=client_name,
        city=city,
        country=country,
    )
    direct_search_urls = [v["url"] for v in search_variants]

    # 2. Harvest Candidates via SerpAPI Google X-Ray
    raw_candidates = harvester_service.harvest_candidates(
        name=client_name,
        city=city,
        country=country,
        company=company_hint,
    )

    # 3. Score & Rank Candidates
    target = LeadTarget(
        name=client_name,
        city=city,
        country=country,
        company_hint=company_hint,
        domain_keywords=[s.strip() for s in (job.skills_tags or "").split(",") if s.strip()],
    )

    scored_candidates = scorer_service.rank_and_separate(target, raw_candidates)

    # 4. Persist to Database & Stage 4 Snapshot
    await scorer_service.persist_candidates(
        job_id=job.id,
        job_uid=job.job_uid,
        scored_candidates=scored_candidates,
        session=db,
    )

    # 5. Format Dual Delivery Response
    resolved_cand = None
    potential_cands = []

    # Reload saved candidates from db
    from app.models.candidate import Candidate
    cand_stmt = (
        select(Candidate)
        .filter_by(job_id=job.id)
        .order_by(Candidate.rank_order)
    )
    cand_res = await db.execute(cand_stmt)
    saved_candidates = cand_res.scalars().all()

    for sc in saved_candidates:
        cand_resp = CandidateResponse.model_validate(sc)
        if sc.is_primary_resolved and not resolved_cand:
            resolved_cand = cand_resp
        else:
            potential_cands.append(cand_resp)

    return LeadDiscoveryResultResponse(
        job_id=job.id,
        job_uid=job.job_uid,
        client_name=client_name,
        location=f"{city}, {country}" if city and country else (city or country or "Unknown"),
        resolved_candidate=resolved_cand,
        potential_candidates=potential_cands,
        direct_linkedin_search_urls=direct_search_urls,
        search_variants=search_variants,
        excel_download_url=f"/api/v1/leads/{job_uid}/export",
    )


@router.get("/export")
async def export_all_leads_excel(
    min_spend: Optional[Decimal] = Query(None, description="Filter jobs by minimum client spend in USD"),
    tier: Optional[str] = Query(None, description="Filter by candidate match tier, e.g. 'Tier A'"),
    country: Optional[str] = Query(None, description="Filter by client country"),
    only_primary: bool = Query(False, description="Export only the primary resolved decision-maker per job"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Exports a sales-ready Master 46-Column Excel Workbook (.xlsx) across all analyzed leads
    with optional filtering by spend, tier, and country.
    """
    file_path = await excel_export_service.export_from_db(
        session=db,
        min_spend=min_spend,
        tier=tier,
        country=country,
        only_primary=only_primary,
    )

    return FileResponse(
        path=str(file_path),
        filename="leads_decision_makers.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/{job_uid}/export")
async def export_job_leads_excel(
    job_uid: str,
    only_primary: bool = Query(False, description="Export only the primary resolved decision-maker"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generates and downloads the sales-ready 46-Column Excel Workbook for a single job lead.
    """
    # Verify job exists
    stmt = select(Job).filter_by(job_uid=job_uid)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_uid} not found.",
        )

    file_path = await excel_export_service.export_from_db(
        session=db,
        job_uid=job_uid,
        only_primary=only_primary,
    )

    return FileResponse(
        path=str(file_path),
        filename=f"{job_uid}_leads.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

