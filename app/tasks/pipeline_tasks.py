import asyncio
import random
import uuid
import zoneinfo
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.models.schedule import ScheduledKeywordSearch, ScheduleExecutionLog
from app.models.session import (
    AsyncSessionLocal,
    TaskAsyncSessionLocal,
    get_task_db_session,
    is_sqlite,
)
from app.services.email_service import email_service
from app.services.excel_export_service import excel_export_service
from app.services.pipeline_service import pipeline_runner
from app.services.scraper_service import scraper_service

logger = get_logger("app.tasks.pipeline")

DAY_ABBREVIATIONS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def calculate_next_run_at(
    schedule: ScheduledKeywordSearch,
    from_time: Optional[datetime] = None,
) -> datetime:
    """
    Calculate the next execution timestamp based on cron schedule or interval hours.
    Uses timezone-aware evaluation via Python standard zoneinfo.ZoneInfo.
    """
    base_time = from_time or datetime.now(timezone.utc)
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    # 1. Frequency type: INTERVAL fallback
    freq = (getattr(schedule, "frequency_type", None) or "").upper()
    if freq == "INTERVAL" or (not freq and getattr(schedule, "interval_hours", None) and not getattr(schedule, "selected_days", None)):
        interval_h = max(1, schedule.interval_hours if schedule.interval_hours else 6)
        return base_time + timedelta(hours=interval_h)

    # 2. Frequency type: CRON / Scheduled Time of Day
    tz_name = getattr(schedule, "timezone", "Asia/Kolkata") or "Asia/Kolkata"
    try:
        target_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception as tz_err:
        logger.warning(
            f"[SCHEDULER] Invalid timezone '{tz_name}' on schedule {getattr(schedule, 'id', 'unknown')}, falling back to UTC: {tz_err}"
        )
        target_tz = zoneinfo.ZoneInfo("UTC")

    time_str = getattr(schedule, "execution_time", "10:30") or "10:30"
    try:
        parts = time_str.strip().split(":")
        target_hour = int(parts[0])
        target_minute = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        target_hour = 10
        target_minute = 30

    # Localize reference time
    from_time_local = base_time.astimezone(target_tz)

    raw_days = getattr(schedule, "selected_days", []) or []
    active_days_set = {
        d.strip().lower()[:3]
        for d in raw_days
        if isinstance(d, str) and d.strip()
    }

    # Evaluate sequentially starting from day 0 (today) up to 14 days ahead
    for day_offset in range(15):
        candidate_date = from_time_local.date() + timedelta(days=day_offset)
        candidate_local = datetime(
            candidate_date.year,
            candidate_date.month,
            candidate_date.day,
            target_hour,
            target_minute,
            0,
            tzinfo=target_tz,
        )
        candidate_day = DAY_ABBREVIATIONS[candidate_local.weekday()]

        if active_days_set and candidate_day not in active_days_set:
            continue

        if candidate_local > from_time_local:
            return candidate_local.astimezone(timezone.utc)

    # Fallback to tomorrow at target time if no selected days matched
    fallback_dt = from_time_local + timedelta(days=1)
    return datetime(
        fallback_dt.year,
        fallback_dt.month,
        fallback_dt.day,
        target_hour,
        target_minute,
        0,
        tzinfo=target_tz,
    ).astimezone(timezone.utc)


async def _async_check_and_dispatch_due_schedules() -> List[str]:
    """
    Inspect active keyword schedules and dispatch Celery tasks for due items.
    Applies SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL to prevent race conditions.
    """
    now_utc = datetime.now(timezone.utc)
    dispatched_ids: List[str] = []

    logger.info(f"[SCHEDULER] Scanning for due keyword search schedules at {now_utc.isoformat()}...")

    async with get_task_db_session() as session:
        try:
            stmt = (
                select(ScheduledKeywordSearch)
                .where(
                    ScheduledKeywordSearch.is_active == True,
                    or_(
                        ScheduledKeywordSearch.next_run_at <= now_utc,
                        ScheduledKeywordSearch.next_run_at.is_(None),
                    ),
                )
                .order_by(ScheduledKeywordSearch.created_at.asc())
            )
            if not is_sqlite:
                stmt = stmt.with_for_update(skip_locked=True)

            result = await session.execute(stmt)
            due_schedules = list(result.scalars().all())

            if not due_schedules:
                logger.info("[SCHEDULER] No due schedules found. Poller sleeping.")
                return []

            logger.info(f"[SCHEDULER] Found {len(due_schedules)} due schedule(s) to dispatch.")

            for sched in due_schedules:
                schedule_id_str = str(sched.id)
                logger.info(
                    f"[SCHEDULER] [DISPATCH] Triggering task for schedule {schedule_id_str} "
                    f"(keyword: '{sched.search_keyword}', user: '{sched.user_identifier}')."
                )

                # Set next_run_at immediately to future run date to prevent duplicate dispatch in subsequent ticks
                sched.next_run_at = calculate_next_run_at(sched, from_time=now_utc)
                session.add(sched)

                # Enqueue Celery task
                execute_scheduled_search_and_email.delay(schedule_id_str)
                dispatched_ids.append(schedule_id_str)

            await session.commit()
            logger.info(f"[SCHEDULER] Successfully dispatched {len(dispatched_ids)} schedule task(s).")
            return dispatched_ids
        except Exception as e:
            await session.rollback()
            logger.error(f"[SCHEDULER] [FAILED] Error scanning due schedules: {e}", exc_info=True)
            return []


@celery_app.task(name="app.tasks.pipeline_tasks.check_and_dispatch_due_schedules")
def check_and_dispatch_due_schedules() -> List[str]:
    """Celery Beat poller to trigger due keyword searches."""
    return asyncio.run(_async_check_and_dispatch_due_schedules())


async def _async_execute_scheduled_search(schedule_id: str) -> Dict[str, Any]:
    """
    Execute complete scraping with human pacing jitter, NLP intelligence mining,
    Excel workbook generation, and diagnostic email notification with error tracking.
    """
    now_utc = datetime.now(timezone.utc)
    logger.info(f"[CELERY] [EXECUTION START] Beginning scheduled search for schedule_id: {schedule_id}")

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        logger.error(f"[CELERY] [FAILED] Invalid schedule_id UUID format: {schedule_id}")
        return {"status": "FAILED", "error": "Invalid UUID"}

    async with get_task_db_session() as session:
        # Step 1: Retrieve schedule configuration
        stmt = select(ScheduledKeywordSearch).where(ScheduledKeywordSearch.id == schedule_uuid)
        result = await session.execute(stmt)
        sched = result.scalar_one_or_none()

        if not sched:
            logger.error(f"[CELERY] [FAILED] Schedule {schedule_id} not found in database.")
            return {"status": "FAILED", "error": "Schedule not found"}

        if not sched.is_active:
            logger.warning(f"[CELERY] [ABORTED] Schedule {schedule_id} is inactive.")
            return {"status": "ABORTED", "error": "Schedule is inactive"}

        # Extract scalar properties to local variables to prevent expired attribute lazy-load issues across async commits/rollbacks
        keyword = sched.search_keyword
        target_limit = sched.target_limit or 10
        user_identifier = sched.user_identifier
        recipient_emails = list(sched.recipient_emails or [])
        email_subject_template = sched.email_subject_template
        min_del = getattr(sched, "min_delay_seconds", 30.0) or 30.0
        max_del = getattr(sched, "max_delay_seconds", 120.0) or 120.0

        # Step 2: Create execution audit log
        log_entry = ScheduleExecutionLog(
            schedule_id=sched.id,
            status="RUNNING",
            started_at=now_utc,
            jobs_scraped=0,
            jobs_expanded=0,
            email_status="PENDING",
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)
        log_entry_id = log_entry.id

        captured_errors: List[Dict[str, Any]] = []

        try:
            logger.info(
                f"[CELERY] [SEARCH] Scraping jobs for keyword: '{keyword}' (target_limit: {target_limit}, user: '{user_identifier}')..."
            )

            # Step 3: Run feed search
            feed_results = await scraper_service.search_feed(
                query=keyword,
                limit=target_limit,
                session=session,
                user_identifier=user_identifier,
            )

            job_items = feed_results.get("jobs", [])
            jobs_scraped = len(job_items)
            logger.info(f"[CELERY] [SCRAPED] Discovered {jobs_scraped} jobs from feed.")

            # Step 4: Expand top jobs with strict sequential human pacing & error capture
            expanded_count = 0
            high_value_count = 0
            lead_highlights: List[Dict[str, Any]] = []
            jobs_to_expand = job_items[:target_limit]

            for idx, item in enumerate(jobs_to_expand, 1):
                job_url = item.get("job_url") or item.get("url")
                if not job_url:
                    continue

                # 4.1. Randomized Human Jitter Delay (0.5 - 2.0 min) to emulate human reading behavior
                if idx > 1:
                    min_del = getattr(sched, "min_delay_seconds", 30.0) or 30.0
                    max_del = getattr(sched, "max_delay_seconds", 120.0) or 120.0
                    delay = random.uniform(min_del, max_del)
                    logger.info(
                        f"[HUMAN JITTER] Pausing {delay:.1f}s before inspecting job {idx}/{len(jobs_to_expand)} to emulate human reading behavior..."
                    )
                    await asyncio.sleep(delay)

                # 4.2. Resilient Execution with Error Capture and intermediate commit
                try:
                    logger.info(
                        f"[CELERY] [EXPAND] Deep inspecting job {idx}/{len(jobs_to_expand)}: {job_url}"
                    )
                    pipeline_res = await pipeline_runner.execute_job_pipeline(
                        job_url=job_url,
                        session=session,
                        auto_confirm=True,
                        apply_delay=True,
                        user_identifier=user_identifier,
                        harvest_candidates=False,
                    )
                    expanded_count += 1

                    has_lead = bool(
                        pipeline_res.get("client_name")
                        and pipeline_res.get("client_name") != "Client"
                    )
                    if has_lead:
                        high_value_count += 1

                    match_score = (
                        round(pipeline_res["primary_resolved_score"] * 100)
                        if pipeline_res.get("primary_resolved_score") is not None
                        else None
                    )
                    lead_highlights.append({
                        "title": pipeline_res.get("job_title") or item.get("title") or "Upwork Lead",
                        "company": pipeline_res.get("company_name") or "Direct Client",
                        "client_name": pipeline_res.get("client_name") or "Unspecified",
                        "decision_maker": pipeline_res.get("client_name") or "Direct Client",
                        "score": match_score,
                    })
                    await session.commit()
                except Exception as job_err:
                    await session.rollback()
                    logger.warning(
                        f"[CELERY] [JOB ERROR] Failure expanding job {job_url}: {job_err}",
                        exc_info=True,
                    )
                    captured_errors.append({
                        "job_url": job_url,
                        "job_index": idx,
                        "error_type": type(job_err).__name__,
                        "message": str(job_err),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            # Step 5: Export Master 34-Column Excel workbook (guaranteeing partial data preservation)
            clean_kw = "".join(c if c.isalnum() else "_" for c in keyword.strip().lower())
            timestamp_str = int(now_utc.timestamp())
            export_filename = f"schedule_{clean_kw}_{timestamp_str}.xlsx"
            export_path = settings.EXPORTS_DIR / export_filename

            logger.info(f"[CELERY] [EXCEL] Exporting Master 34-Column workbook to {export_path}...")
            generated_path = await excel_export_service.export_from_db(
                session=session,
                query=keyword,
                output_path=export_path,
            )

            # Step 6: Dispatch Diagnostic Email Report
            email_status = "SKIPPED"
            if recipient_emails:
                stats = {
                    "jobs_scraped": jobs_scraped,
                    "jobs_expanded": expanded_count,
                    "high_value_leads": high_value_count,
                    "lead_highlights": lead_highlights[:5],
                }
                email_res = await email_service.send_excel_report_email_async(
                    recipient_emails=recipient_emails,
                    keyword=keyword,
                    excel_file_path=Path(generated_path),
                    stats=stats,
                    subject_override=email_subject_template,
                    error_logs=captured_errors if captured_errors else None,
                )
                email_status = email_res.get("status", "SENT")

            # Step 7: Update execution log & schedule status
            completed_utc = datetime.now(timezone.utc)
            final_status = "PARTIAL_SUCCESS" if captured_errors and expanded_count > 0 else (
                "FAILED" if captured_errors and expanded_count == 0 else "SUCCESS"
            )
            log_entry.status = final_status
            log_entry.jobs_scraped = jobs_scraped
            log_entry.jobs_expanded = expanded_count
            log_entry.excel_file_path = str(generated_path)
            log_entry.email_status = email_status
            log_entry.completed_at = completed_utc
            if captured_errors:
                log_entry.error_message = f"{len(captured_errors)} job(s) failed during expansion: " + "; ".join(
                    f"{e.get('job_url')}: {e.get('message')}" for e in captured_errors[:3]
                )

            sched.last_run_at = completed_utc
            sched.next_run_at = calculate_next_run_at(sched, from_time=completed_utc)

            session.add(log_entry)
            session.add(sched)
            await session.commit()

            logger.info(
                f"[CELERY] [{final_status}] Completed pipeline execution for schedule {schedule_id}. "
                f"Jobs: {jobs_scraped}, Expanded: {expanded_count}, Errors: {len(captured_errors)}, Email: {email_status}."
            )
            return {
                "status": final_status,
                "schedule_id": schedule_id,
                "jobs_scraped": jobs_scraped,
                "jobs_expanded": expanded_count,
                "excel_path": str(generated_path),
                "email_status": email_status,
                "errors_captured": len(captured_errors),
            }

        except Exception as e:
            await session.rollback()
            completed_utc = datetime.now(timezone.utc)
            logger.error(f"[CELERY] [FAILED] Execution failed for schedule {schedule_id}: {e}", exc_info=True)

            # Record failure in audit log and advance schedule
            try:
                log_to_update = await session.get(ScheduleExecutionLog, log_entry_id)
                if log_to_update:
                    log_to_update.status = "FAILED"
                    log_to_update.error_message = str(e)
                    log_to_update.completed_at = completed_utc
                    session.add(log_to_update)

                sched_to_update = await session.get(ScheduledKeywordSearch, schedule_uuid)
                if sched_to_update:
                    sched_to_update.last_run_at = completed_utc
                    sched_to_update.next_run_at = calculate_next_run_at(sched_to_update, from_time=completed_utc)
                    session.add(sched_to_update)

                await session.commit()
            except Exception as update_err:
                logger.warning(f"[CELERY] Could not update execution log on failure: {update_err}")

            # Attempt diagnostic failure email delivery using local variables (safe from lazy-load errors)
            if recipient_emails:
                try:
                    await email_service.send_excel_report_email_async(
                        recipient_emails=recipient_emails,
                        keyword=keyword,
                        excel_file_path=None,
                        stats={"jobs_scraped": 0, "jobs_expanded": 0, "high_value_leads": 0},
                        subject_override=f"[FAILED] Upwork Schedule Alert for '{keyword}'",
                        error_logs=[{
                            "job_url": "N/A",
                            "job_index": 0,
                            "error_type": type(e).__name__,
                            "message": str(e),
                            "timestamp": completed_utc.isoformat(),
                        }],
                        error_summary=f"Automated pipeline halted: {str(e)}",
                    )
                except Exception as mail_err:
                    logger.warning(f"[EMAIL] [FAILED] Failed sending error notification: {mail_err}")

            return {
                "status": "FAILED",
                "schedule_id": schedule_id,
                "error": str(e),
            }


@celery_app.task(
    name="app.tasks.pipeline_tasks.execute_scheduled_search_and_email",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def execute_scheduled_search_and_email(self, schedule_id: str) -> Dict[str, Any]:
    """Execute scheduled keyword search pipeline, generate Excel, and dispatch email."""
    try:
        return asyncio.run(_async_execute_scheduled_search(schedule_id))
    except Exception as exc:
        logger.error(
            f"[CELERY] [TASK ERROR] Task failed for schedule {schedule_id}: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc)
