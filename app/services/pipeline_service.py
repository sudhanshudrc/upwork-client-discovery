import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.rate_limiter import apply_jitter_delay
from app.models.candidate import Candidate
from app.models.client import Client
from app.models.contract import ClientContract
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.schemas.intelligence import UserConfirmationRequest
from app.services.excel_export_service import excel_export_service
from app.services.geo_resolver_service import geo_resolver
from app.services.harvester_service import harvester_service
from app.services.nlp_service import nlp_service
from app.services.scorer_service import LeadTarget, scorer_service
from app.services.scraper_service import scraper_service

logger = logging.getLogger(__name__)


class BatchPipelineRunner:
    """
    Autonomous End-to-End Discovery Pipeline:
    Executes feed ingestion -> contract expansion -> NLP mining ->
    LinkedIn harvesting -> 4-factor scoring -> Excel generation.
    """

    def __init__(self):
        self._active_runs: Dict[str, Dict[str, Any]] = {}

    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._active_runs.get(run_id)

    async def execute_job_pipeline(
        self,
        job_url: str,
        session: AsyncSession,
        auto_confirm: bool = True,
        apply_delay: bool = True,
        user_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs the full 5-stage pipeline for an individual job:
        1. Anti-blocking rate-limiting jitter (8–15s).
        2. Deep scrape and 30+ history expansion (strict partitioning).
        3. spaCy NLP client name and organization discovery.
        4. SerpAPI Google X-Ray candidate harvesting.
        5. 4-factor composite scoring and database sync (Tier A Resolved vs Potential).
        """
        logger.info(f"[PIPELINE START] Processing job: {job_url} (user: {user_identifier or 'default'})")

        # Step 1: Jitter delay
        jitter_slept = 0.0
        if apply_delay:
            logger.info("[STEP 1/5] Applying anti-blocking jitter delay...")
            jitter_slept = await apply_jitter_delay(action_label=f"scrape_{job_url}")
            logger.info(f"[STEP 1/5] Resumed after {jitter_slept:.1f}s jitter sleep.")
        else:
            logger.debug("[STEP 1/5] Jitter delay bypassed.")

        try:
            # Step 2: Deep scrape & sync to database
            logger.info(f"[STEP 2/5] Deep scraping job DOM and expanding contract history: {job_url}")
            parsed_job = await scraper_service.scrape_job_details(
                job_url=job_url,
                expand_all_history=True,
                session=session,
                user_identifier=user_identifier,
            )
            logger.info(
                f"[STEP 2/5] Job scraped successfully: '{parsed_job.get('title')}' "
                f"(Contracts: {len(parsed_job.get('contracts', []))}, Client: {parsed_job.get('client', {}).get('city')}, {parsed_job.get('client', {}).get('country')})"
            )

            # Retrieve synchronized DB Job model with relationships
            stmt = (
                select(Job)
                .filter_by(job_uid=parsed_job["job_uid"])
                .options(
                    selectinload(Job.client),
                    selectinload(Job.intelligence),
                )
            )
            res = await session.execute(stmt)
            db_job = res.scalars().one()

            # Step 3: Load contracts and extract NLP intelligence
            contract_stmt = select(ClientContract).filter_by(client_id=db_job.client_id)
            c_res = await session.execute(contract_stmt)
            contracts = c_res.scalars().all()
            contract_dicts = [c.to_dict() for c in contracts]

            logger.info(f"[STEP 3/5] Running spaCy NLP & Linguistic mining across {len(contracts)} contracts...")
            intel_res = await nlp_service.analyze_job_intelligence(
                job_id=db_job.id,
                job_uid=db_job.job_uid,
                job_description=db_job.description,
                contracts=contract_dicts,
                session=session,
            )
            logger.info(
                f"[STEP 3/5] Intelligence extracted: Suggested Client='{intel_res.suggested_client_name}', "
                f"Company='{intel_res.suggested_company_name}', Agency={intel_res.is_agency}"
            )

            # Step 4: Client name resolution & Auto-Confirmation
            client_name = "Client"
            company_name = None
            if auto_confirm and intel_res.suggested_client_name:
                top_name = intel_res.suggested_client_name
                top_comp = intel_res.suggested_company_name
                confirm_req = UserConfirmationRequest(
                    job_id=db_job.id,
                    confirmed_client_name=top_name,
                    confirmed_company_name=top_comp,
                    target_role="CTO",
                )
                await nlp_service.confirm_intelligence(confirm_req, session)
                client_name = top_name
                company_name = top_comp
                logger.info(f"[STEP 4/5] Auto-confirmed target decision maker: '{client_name}' (Company: '{company_name}')")
            elif db_job.intelligence and db_job.intelligence.confirmed_client_name:
                client_name = db_job.intelligence.confirmed_client_name
                company_name = db_job.intelligence.confirmed_company_name
                logger.info(f"[STEP 4/5] Using previously confirmed target: '{client_name}'")
            else:
                logger.warning("[STEP 4/5] No confident client name detected; using fallback target.")

            city = db_job.client.city if db_job.client else None
            country = db_job.client.country if db_job.client else None

            # Step 5: LinkedIn Harvesting via SerpAPI Google X-Ray
            logger.info(f"[STEP 5/5] Harvesting LinkedIn profiles via Google X-Ray for '{client_name}' in {city}, {country} (Company: {company_name})...")
            raw_candidates = harvester_service.harvest_candidates(
                name=client_name,
                city=city,
                country=country,
                company=company_name,
            )
            logger.info(f"[STEP 5/5] Google X-Ray harvested {len(raw_candidates)} raw candidate profile(s).")

            # Step 6: 4-Factor Composite Scoring
            logger.info("[SCORING] Executing 4-Factor Composite Scoring (Name 40%, Geo 35%, Role 15%, Company 10%)...")
            target = LeadTarget(
                name=client_name,
                city=city,
                country=country,
                company_hint=company_name,
                domain_keywords=[
                    s.strip() for s in (db_job.skills_tags or "").split(",") if s.strip()
                ],
            )

            scored_candidates = scorer_service.rank_and_separate(target, raw_candidates)

            # Step 7: Persist Dual Candidates & Stage 4 Snapshot
            snapshot_payload = await scorer_service.persist_candidates(
                job_id=db_job.id,
                job_uid=db_job.job_uid,
                scored_candidates=scored_candidates,
                session=session,
            )

            resolved_name = (
                scored_candidates[0].candidate.full_name
                if scored_candidates and scored_candidates[0].is_primary_resolved
                else None
            )
            resolved_score = (
                scored_candidates[0].score
                if scored_candidates and scored_candidates[0].is_primary_resolved
                else None
            )

            if resolved_name:
                logger.info(f"[PIPELINE SUCCESS] Resolved Primary Decision Maker: '{resolved_name}' (Score: {resolved_score * 100:.1f}%, Tier: {scored_candidates[0].tier})")
            else:
                logger.info(f"[PIPELINE COMPLETED] Finished with {len(scored_candidates)} potential candidate(s). No single Tier A primary resolved.")

            return {
                "job_uid": db_job.job_uid,
                "job_title": db_job.title,
                "job_url": db_job.job_url,
                "client_name": client_name,
                "company_name": company_name,
                "total_contracts": len(contracts),
                "total_candidates": len(scored_candidates),
                "primary_resolved_name": resolved_name,
                "primary_resolved_score": resolved_score,
                "jitter_slept_seconds": round(jitter_slept, 2),
                "status": "COMPLETED",
            }
        except Exception as e:
            logger.error(f"[PIPELINE FAILED] Failed processing job {job_url}: {e}", exc_info=True)
            raise

    async def execute_batch_pipeline(
        self,
        search_query: str,
        max_jobs: int = 15,
        min_spend: Optional[Decimal] = None,
        auto_confirm: bool = True,
        apply_delay: bool = True,
        session: Optional[AsyncSession] = None,
        user_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end autonomous discovery across a batch of top jobs:
        1. Ingests search feed.
        2. Filters out low-value jobs.
        3. Sequentially expands, extracts, and enriches each job with rate-limiting jitter.
        4. Exports final sales-ready Master 46-Column Excel workbook.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        self._active_runs[run_id] = {
            "run_id": run_id,
            "search_query": search_query,
            "status": "IN_PROGRESS",
            "started_at": started_at.isoformat(),
            "total_jobs_target": max_jobs,
            "processed_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "jobs_summary": [],
            "excel_path": None,
        }

        # Step 1: Search Feed Ingestion
        feed_results = await scraper_service.search_feed(
            query=search_query,
            limit=max_jobs,
            session=session,
            user_identifier=user_identifier,
        )

        job_items = feed_results.get("jobs", [])
        if not job_items:
            self._active_runs[run_id]["status"] = "COMPLETED"
            self._active_runs[run_id]["message"] = "No jobs found for query."
            return self._active_runs[run_id]

        # Limit to target count
        target_jobs = job_items[:max_jobs]
        successful_jobs = []

        for idx, item in enumerate(target_jobs, 1):
            job_url = item.get("job_url")
            if not job_url:
                continue

            try:
                # Apply jitter between sequential jobs
                apply_jitter = apply_delay and (idx > 1)
                summary = await self.execute_job_pipeline(
                    job_url=job_url,
                    session=session,
                    auto_confirm=auto_confirm,
                    apply_delay=apply_jitter,
                    user_identifier=user_identifier,
                )
                self._active_runs[run_id]["jobs_summary"].append(summary)
                self._active_runs[run_id]["successful_count"] += 1
                successful_jobs.append(summary)
            except Exception as e:
                logger.error(f"Error processing job {job_url}: {e}", exc_info=True)
                self._active_runs[run_id]["jobs_summary"].append({
                    "job_url": job_url,
                    "status": "FAILED",
                    "error": str(e),
                })
                self._active_runs[run_id]["failed_count"] += 1

            self._active_runs[run_id]["processed_count"] = idx

        # Step 2: Export Master Excel Workbook
        excel_path = None
        if session and self._active_runs[run_id]["successful_count"] > 0:
            excel_path = await excel_export_service.export_from_db(
                session=session,
                min_spend=min_spend,
                output_path=settings.EXPORTS_DIR / f"batch_run_{run_id}.xlsx",
            )
            self._active_runs[run_id]["excel_path"] = str(excel_path)

        completed_at = datetime.now(timezone.utc)
        self._active_runs[run_id]["status"] = "COMPLETED"
        self._active_runs[run_id]["completed_at"] = completed_at.isoformat()
        self._active_runs[run_id]["duration_seconds"] = round(
            (completed_at - started_at).total_seconds(), 2
        )

        return self._active_runs[run_id]


pipeline_runner = BatchPipelineRunner()
