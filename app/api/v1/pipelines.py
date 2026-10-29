from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import get_db_session
from app.services.pipeline_service import pipeline_runner


router = APIRouter(prefix="/pipelines", tags=["Batch Pipelines & Automation"])


class BatchRunRequest(BaseModel):
    search_query: str = Field(..., description="Upwork search query (e.g. 'automation', 'fastapi')")
    max_jobs: int = Field(default=5, ge=1, le=30, description="Maximum jobs to process in this run")
    min_spend: Optional[Decimal] = Field(default=None, description="Optional minimum client spend filter")
    auto_confirm: bool = Field(default=True, description="Auto-confirm highest confidence client name")
    apply_delay: bool = Field(default=True, description="Apply anti-blocking jitter (8-15s)")
    user_identifier: Optional[str] = Field(default=None, description="Optional user identifier for multi-tenant sessions")


class SingleJobRunRequest(BaseModel):
    job_url: str = Field(..., description="Full Upwork job URL to run through entire pipeline")
    auto_confirm: bool = Field(default=True, description="Auto-confirm highest confidence client name")
    apply_delay: bool = Field(default=False, description="Apply anti-blocking jitter")
    user_identifier: Optional[str] = Field(default=None, description="Optional user identifier for multi-tenant sessions")


@router.post("/batch-run")
async def trigger_batch_pipeline(
    request: BatchRunRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Triggers the end-to-end autonomous discovery pipeline across search feed jobs:
    1. Ingests top jobs from feed.
    2. Deep scrapes each job & expands 30+ contracts with anti-blocking jitter.
    3. Mines client & company names with spaCy NLP.
    4. Harvests LinkedIn candidates via SerpAPI Google X-Ray.
    5. Scores candidates and commits Dual Delivery (Tier A Resolved vs Potential).
    6. Generates sales-ready Master 46-Column Excel export.
    """
    result = await pipeline_runner.execute_batch_pipeline(
        search_query=request.search_query,
        max_jobs=request.max_jobs,
        min_spend=request.min_spend,
        auto_confirm=request.auto_confirm,
        apply_delay=request.apply_delay,
        session=db,
        user_identifier=request.user_identifier,
    )
    return result


@router.post("/job-run")
async def trigger_single_job_pipeline(
    request: SingleJobRunRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Executes the end-to-end discovery pipeline for a single job URL.
    """
    result = await pipeline_runner.execute_job_pipeline(
        job_url=request.job_url,
        session=db,
        auto_confirm=request.auto_confirm,
        apply_delay=request.apply_delay,
        user_identifier=request.user_identifier,
    )
    return result


@router.get("/status/{run_id}")
async def get_batch_run_status(run_id: str):
    """
    Retrieves progress and summary of an active or completed batch pipeline run.
    """
    status_info = pipeline_runner.get_run_status(run_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{run_id}' not found.",
        )
    return status_info

