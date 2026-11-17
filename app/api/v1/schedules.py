import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.schedule import ScheduledKeywordSearch, ScheduleExecutionLog
from app.models.session import get_db_session
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleExecutionLogResponse,
    ScheduleResponse,
    ScheduleTriggerResponse,
    ScheduleUpdateRequest,
)
from app.tasks.pipeline_tasks import (
    calculate_next_run_at,
    execute_scheduled_search_and_email,
)

logger = get_logger("app.api.v1.schedules")

router = APIRouter(prefix="/schedules", tags=["Scheduled Automation & Celery"])


def _to_schedule_response(sched: ScheduledKeywordSearch) -> ScheduleResponse:
    """Format SQLAlchemy ScheduledKeywordSearch model into ScheduleResponse schema."""
    latest_log = None
    insp = inspect(sched)
    if "execution_logs" not in insp.unloaded and sched.execution_logs:
        log_obj = sched.execution_logs[0]
        latest_log = ScheduleExecutionLogResponse(
            id=str(log_obj.id),
            schedule_id=str(log_obj.schedule_id),
            status=log_obj.status,
            jobs_scraped=log_obj.jobs_scraped,
            jobs_expanded=log_obj.jobs_expanded,
            excel_file_path=log_obj.excel_file_path,
            email_status=log_obj.email_status,
            error_message=log_obj.error_message,
            started_at=log_obj.started_at,
            completed_at=log_obj.completed_at,
            created_at=log_obj.created_at,
        )

    return ScheduleResponse(
        id=str(sched.id),
        user_identifier=sched.user_identifier,
        search_keyword=sched.search_keyword,
        target_limit=sched.target_limit,
        frequency_type=sched.frequency_type,
        execution_time=getattr(sched, "execution_time", "10:30") or "10:30",
        selected_days=getattr(sched, "selected_days", []) or [],
        timezone=getattr(sched, "timezone", "Asia/Kolkata") or "Asia/Kolkata",
        interval_hours=sched.interval_hours,
        cron_expression=sched.cron_expression,
        min_delay_seconds=getattr(sched, "min_delay_seconds", 30.0) if getattr(sched, "min_delay_seconds", None) is not None else 30.0,
        max_delay_seconds=getattr(sched, "max_delay_seconds", 120.0) if getattr(sched, "max_delay_seconds", None) is not None else 120.0,
        recipient_emails=sched.recipient_emails or [],
        email_subject_template=sched.email_subject_template,
        is_active=sched.is_active,
        last_run_at=sched.last_run_at,
        next_run_at=sched.next_run_at,
        created_at=sched.created_at,
        updated_at=sched.updated_at,
        latest_execution=latest_log,
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreateRequest,
    user_identifier: str = Query("default", description="User or tenant identifier"),
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleResponse:
    """Create a new periodic keyword search schedule with automated Excel email delivery."""
    logger.info(
        f"[SCHEDULER] Creating schedule for keyword: '{payload.search_keyword}' "
        f"(user: '{user_identifier}', time: '{payload.execution_time}', days: {payload.selected_days})..."
    )

    sched = ScheduledKeywordSearch(
        user_identifier=user_identifier,
        search_keyword=payload.search_keyword.strip(),
        target_limit=payload.target_limit,
        frequency_type=payload.frequency_type.upper(),
        execution_time=payload.execution_time,
        selected_days=[d.strip().lower() for d in payload.selected_days],
        timezone=payload.timezone,
        interval_hours=payload.interval_hours,
        cron_expression=payload.cron_expression,
        min_delay_seconds=payload.min_delay_seconds,
        max_delay_seconds=payload.max_delay_seconds,
        recipient_emails=[str(e) for e in payload.recipient_emails],
        email_subject_template=payload.email_subject_template,
        is_active=payload.is_active,
    )
    sched.next_run_at = calculate_next_run_at(sched, from_time=datetime.now(timezone.utc))

    db.add(sched)
    await db.commit()
    await db.refresh(sched)

    logger.info(f"[SCHEDULER] Successfully created schedule: {sched.id} (next_run: {sched.next_run_at})")
    return _to_schedule_response(sched)


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    user_identifier: Optional[str] = Query(None, description="Filter by user identifier"),
    active_only: bool = Query(False, description="Filter active schedules only"),
    db: AsyncSession = Depends(get_db_session),
) -> List[ScheduleResponse]:
    """List all scheduled keyword search automations."""
    stmt = (
        select(ScheduledKeywordSearch)
        .options(selectinload(ScheduledKeywordSearch.execution_logs))
        .order_by(desc(ScheduledKeywordSearch.created_at))
    )

    if user_identifier:
        stmt = stmt.where(ScheduledKeywordSearch.user_identifier == user_identifier)
    if active_only:
        stmt = stmt.where(ScheduledKeywordSearch.is_active == True)

    res = await db.execute(stmt)
    schedules = list(res.scalars().all())

    return [_to_schedule_response(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleResponse:
    """Fetch details of a single scheduled keyword search by its UUID."""
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule_id UUID format: '{schedule_id}'",
        )

    stmt = (
        select(ScheduledKeywordSearch)
        .options(selectinload(ScheduledKeywordSearch.execution_logs))
        .where(ScheduledKeywordSearch.id == schedule_uuid)
    )
    res = await db.execute(stmt)
    sched = res.scalar_one_or_none()

    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' was not found.",
        )

    return _to_schedule_response(sched)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleResponse:
    """Update settings for an existing keyword search schedule."""
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule_id UUID format: '{schedule_id}'",
        )

    stmt = (
        select(ScheduledKeywordSearch)
        .options(selectinload(ScheduledKeywordSearch.execution_logs))
        .where(ScheduledKeywordSearch.id == schedule_uuid)
    )
    res = await db.execute(stmt)
    sched = res.scalar_one_or_none()

    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' was not found.",
        )

    # Apply updates
    time_related_updated = False
    if payload.search_keyword is not None:
        sched.search_keyword = payload.search_keyword.strip()
    if payload.target_limit is not None:
        sched.target_limit = payload.target_limit
    if payload.frequency_type is not None:
        sched.frequency_type = payload.frequency_type.upper()
        time_related_updated = True
    if payload.execution_time is not None:
        sched.execution_time = payload.execution_time
        time_related_updated = True
    if payload.selected_days is not None:
        sched.selected_days = [d.strip().lower() for d in payload.selected_days]
        time_related_updated = True
    if payload.timezone is not None:
        sched.timezone = payload.timezone
        time_related_updated = True
    if payload.interval_hours is not None:
        sched.interval_hours = payload.interval_hours
        time_related_updated = True
    if payload.cron_expression is not None:
        sched.cron_expression = payload.cron_expression
    if payload.min_delay_seconds is not None:
        sched.min_delay_seconds = payload.min_delay_seconds
    if payload.max_delay_seconds is not None:
        sched.max_delay_seconds = payload.max_delay_seconds
    if payload.recipient_emails is not None:
        sched.recipient_emails = [str(e) for e in payload.recipient_emails]
    if payload.email_subject_template is not None:
        sched.email_subject_template = payload.email_subject_template
    if payload.is_active is not None:
        sched.is_active = payload.is_active
        if sched.is_active and not sched.next_run_at:
            time_related_updated = True

    if time_related_updated and sched.is_active:
        sched.next_run_at = calculate_next_run_at(sched, from_time=datetime.now(timezone.utc))

    await db.commit()
    await db.refresh(sched)
    logger.info(f"[SCHEDULER] Updated schedule {schedule_id}.")
    return _to_schedule_response(sched)


@router.delete("/{schedule_id}", status_code=status.HTTP_200_OK)
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a schedule and its historical execution logs."""
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule_id UUID format: '{schedule_id}'",
        )

    stmt = select(ScheduledKeywordSearch).where(ScheduledKeywordSearch.id == schedule_uuid)
    res = await db.execute(stmt)
    sched = res.scalar_one_or_none()

    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' was not found.",
        )

    await db.delete(sched)
    await db.commit()
    logger.info(f"[SCHEDULER] Deleted schedule {schedule_id}.")
    return {"status": "SUCCESS", "message": f"Schedule {schedule_id} deleted successfully."}


@router.post("/{schedule_id}/trigger-now", response_model=ScheduleTriggerResponse)
async def trigger_schedule_now(
    schedule_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ScheduleTriggerResponse:
    """Manually dispatch a background Celery execution for this schedule immediately."""
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule_id UUID format: '{schedule_id}'",
        )

    stmt = select(ScheduledKeywordSearch).where(ScheduledKeywordSearch.id == schedule_uuid)
    res = await db.execute(stmt)
    sched = res.scalar_one_or_none()

    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' was not found.",
        )

    # Dispatch to Celery queue immediately
    task = execute_scheduled_search_and_email.delay(schedule_id)
    logger.info(
        f"[SCHEDULER] [TRIGGER NOW] Enqueued immediate execution for schedule {schedule_id} (Celery Task ID: {task.id})."
    )

    return ScheduleTriggerResponse(
        message="Scheduled keyword search dispatched to Celery background worker.",
        task_id=str(task.id),
        schedule_id=schedule_id,
    )


@router.get("/{schedule_id}/logs", response_model=List[ScheduleExecutionLogResponse])
async def get_schedule_logs(
    schedule_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> List[ScheduleExecutionLogResponse]:
    """Retrieve historical execution logs for a schedule."""
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule_id UUID format: '{schedule_id}'",
        )

    stmt = (
        select(ScheduleExecutionLog)
        .where(ScheduleExecutionLog.schedule_id == schedule_uuid)
        .order_by(desc(ScheduleExecutionLog.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    return [
        ScheduleExecutionLogResponse(
            id=str(log.id),
            schedule_id=str(log.schedule_id),
            status=log.status,
            jobs_scraped=log.jobs_scraped,
            jobs_expanded=log.jobs_expanded,
            excel_file_path=log.excel_file_path,
            email_status=log.email_status,
            error_message=log.error_message,
            started_at=log.started_at,
            completed_at=log.completed_at,
            created_at=log.created_at,
        )
        for log in logs
    ]
