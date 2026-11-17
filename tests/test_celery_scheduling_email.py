import re
import uuid
import zoneinfo
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.main import app
from app.models.base import Base
from app.models.schedule import ScheduledKeywordSearch, ScheduleExecutionLog
from app.models.session import get_db_session
from app.services.email_service import EmailService, email_service
from app.tasks.pipeline_tasks import calculate_next_run_at


def test_schedule_models_ddl_and_relationships():
    """Verify that ScheduledKeywordSearch and ScheduleExecutionLog compile valid DDL and support relationships."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert "scheduled_keyword_searches" in Base.metadata.tables
    assert "schedule_execution_logs" in Base.metadata.tables

    with Session(engine) as session:
        # Create Schedule
        sched = ScheduledKeywordSearch(
            user_identifier="test_user",
            search_keyword="ai agent developer",
            target_limit=10,
            frequency_type="CRON",
            execution_time="10:30",
            selected_days=["wed", "thu", "fri", "sat", "sun"],
            timezone="Asia/Kolkata",
            min_delay_seconds=30.0,
            max_delay_seconds=120.0,
            recipient_emails=["leads@example.com"],
            is_active=True,
        )
        session.add(sched)
        session.commit()
        session.refresh(sched)

        assert sched.id is not None
        assert sched.search_keyword == "ai agent developer"
        assert sched.execution_time == "10:30"
        assert sched.selected_days == ["wed", "thu", "fri", "sat", "sun"]
        assert sched.recipient_emails == ["leads@example.com"]

        # Create Execution Log
        log_entry = ScheduleExecutionLog(
            schedule_id=sched.id,
            status="SUCCESS",
            jobs_scraped=15,
            jobs_expanded=5,
            excel_file_path="/tmp/test_report.xlsx",
            email_status="SENT",
        )
        session.add(log_entry)
        session.commit()
        session.refresh(sched)

        assert len(sched.execution_logs) == 1
        assert sched.execution_logs[0].jobs_scraped == 15
        assert sched.execution_logs[0].status == "SUCCESS"

        # Cascade Delete Verification
        session.delete(sched)
        session.commit()

        remaining_logs = session.execute(select(ScheduleExecutionLog)).scalars().all()
        assert len(remaining_logs) == 0


def test_calculate_next_run_at_interval():
    """Verify next run timestamp calculation based on interval hours."""
    sched = ScheduledKeywordSearch(
        user_identifier="test_user",
        search_keyword="python",
        frequency_type="INTERVAL",
        interval_hours=8,
    )
    base_time = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
    next_run = calculate_next_run_at(sched, from_time=base_time)

    assert next_run == datetime(2026, 11, 16, 20, 0, 0, tzinfo=timezone.utc)


def test_timezone_aware_next_run_calculation():
    """
    Verify timezone-aware calculation for CRON scheduled runs:
    - Monday rolls forward to Wednesday 10:30 AM
    - Tuesday rolls forward to Wednesday 10:30 AM
    - Sunday after 10:30 AM rolls forward to Wednesday 10:30 AM
    - Correct UTC conversion across daylight saving / standard time
    """
    kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    sched = ScheduledKeywordSearch(
        user_identifier="test_user",
        search_keyword="ai agent developer",
        frequency_type="CRON",
        execution_time="10:30",
        selected_days=["wed", "thu", "fri", "sat", "sun"],
        timezone="Asia/Kolkata",
    )

    # 1. Monday morning (9:00 AM IST) -> Next run is Wednesday 10:30 AM IST (05:00 UTC)
    mon_base = datetime(2026, 11, 16, 9, 0, 0, tzinfo=kolkata_tz).astimezone(timezone.utc)
    next_run_mon = calculate_next_run_at(sched, from_time=mon_base)
    expected_wed = datetime(2026, 11, 18, 5, 0, 0, tzinfo=timezone.utc)
    assert next_run_mon == expected_wed

    # 2. Tuesday late morning (11:00 AM IST) -> Rolls forward to Wednesday 10:30 AM IST (05:00 UTC)
    tue_base = datetime(2026, 11, 17, 11, 0, 0, tzinfo=kolkata_tz).astimezone(timezone.utc)
    next_run_tue = calculate_next_run_at(sched, from_time=tue_base)
    assert next_run_tue == expected_wed

    # 3. Sunday after 10:30 AM (11:00 AM IST) -> Rolls forward to Wednesday 10:30 AM IST (05:00 UTC next week)
    sun_base = datetime(2026, 11, 22, 11, 0, 0, tzinfo=kolkata_tz).astimezone(timezone.utc)
    next_run_sun = calculate_next_run_at(sched, from_time=sun_base)
    expected_next_wed = datetime(2026, 11, 25, 5, 0, 0, tzinfo=timezone.utc)
    assert next_run_sun == expected_next_wed

    # 4. Wednesday before 10:30 AM (10:00 AM IST) -> Runs today at 10:30 AM IST (05:00 UTC)
    wed_early = datetime(2026, 11, 18, 10, 0, 0, tzinfo=kolkata_tz).astimezone(timezone.utc)
    next_run_wed = calculate_next_run_at(sched, from_time=wed_early)
    assert next_run_wed == expected_wed

    # 5. Daylight Saving Time / Standard Time verification for America/New_York
    ny_sched = ScheduledKeywordSearch(
        user_identifier="test_user",
        search_keyword="fastapi",
        frequency_type="CRON",
        execution_time="10:30",
        selected_days=["wed"],
        timezone="America/New_York",
    )
    # Winter EST (UTC-5): 10:30 AM EST is 15:30 UTC
    winter_base = datetime(2026, 12, 1, 8, 0, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")).astimezone(timezone.utc)
    winter_next = calculate_next_run_at(ny_sched, from_time=winter_base)
    assert winter_next == datetime(2026, 12, 2, 15, 30, 0, tzinfo=timezone.utc)

    # Summer EDT (UTC-4): 10:30 AM EDT is 14:30 UTC
    summer_base = datetime(2026, 7, 7, 8, 0, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")).astimezone(timezone.utc)
    summer_next = calculate_next_run_at(ny_sched, from_time=summer_base)
    assert summer_next == datetime(2026, 7, 8, 14, 30, 0, tzinfo=timezone.utc)


def test_email_service_simulation_mode(tmp_path):
    """Verify EmailService safely simulates email dispatch when SMTP credentials are unconfigured."""
    dummy_excel = tmp_path / "test_leads.xlsx"
    dummy_excel.write_text("dummy binary content")

    svc = EmailService()
    svc.user = None
    svc.password = None

    assert svc.is_configured() is False

    result = svc.send_excel_report_email(
        recipient_emails=["client@example.com"],
        keyword="fastapi automation",
        excel_file_path=dummy_excel,
        stats={"jobs_scraped": 10, "jobs_expanded": 4, "high_value_leads": 4},
    )

    assert result["status"] == "SIMULATED"
    assert "client@example.com" in result["recipients"]
    assert str(dummy_excel) in result["excel_file"]


def test_email_service_diagnostic_error_attachment(tmp_path):
    """Verify that EmailService constructs MIME message with diagnostic error log attached."""
    dummy_excel = tmp_path / "test_leads.xlsx"
    dummy_excel.write_text("dummy content")

    svc = EmailService()
    captured_errors = [
        {
            "job_url": "https://www.upwork.com/jobs/~01abc",
            "job_index": 2,
            "error_type": "TimeoutError",
            "message": "Timed out waiting for DOM element",
            "timestamp": "2026-11-16T10:30:00Z",
        }
    ]

    msg = svc._build_email_message(
        recipient_emails=["ops@example.com"],
        subject="[Test] Diagnostic Pipeline Execution",
        keyword="nlp extraction",
        excel_file_path=dummy_excel,
        stats={"jobs_scraped": 5, "jobs_expanded": 2, "high_value_leads": 2},
        error_logs=captured_errors,
        error_summary="1 job failed to expand due to timeout.",
    )

    # Verify attachment headers
    attachments = [part.get_filename() for part in msg.walk() if part.get_filename()]
    assert "test_leads.xlsx" in attachments
    assert "pipeline_execution_errors.log" in attachments


@pytest.fixture
async def schedules_test_db():
    """Isolated SQLite async session fixture for Schedules API testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_schedules_crud_api_and_trigger(schedules_test_db):
    """Verify complete CRUD lifecycle and Celery immediate trigger for keyword schedules."""
    client = TestClient(app)

    # 1. Create Schedule with cron fields
    create_payload = {
        "search_keyword": "langgraph engineer",
        "target_limit": 10,
        "frequency_type": "CRON",
        "execution_time": "10:30",
        "selected_days": ["wed", "thu", "fri", "sat", "sun"],
        "timezone": "Asia/Kolkata",
        "min_delay_seconds": 30.0,
        "max_delay_seconds": 120.0,
        "recipient_emails": ["analytics@corp.com", "sales@corp.com"],
        "email_subject_template": "Weekly LangGraph Report",
        "is_active": True,
    }
    create_resp = client.post("/api/v1/schedules?user_identifier=test_admin", json=create_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()

    schedule_id = created_data["id"]
    assert created_data["search_keyword"] == "langgraph engineer"
    assert created_data["user_identifier"] == "test_admin"
    assert created_data["execution_time"] == "10:30"
    assert created_data["selected_days"] == ["wed", "thu", "fri", "sat", "sun"]
    assert created_data["timezone"] == "Asia/Kolkata"
    assert created_data["min_delay_seconds"] == 30.0
    assert created_data["max_delay_seconds"] == 120.0
    assert len(created_data["recipient_emails"]) == 2
    assert created_data["next_run_at"] is not None

    # 2. List Schedules
    list_resp = client.get("/api/v1/schedules?user_identifier=test_admin")
    assert list_resp.status_code == 200
    schedules = list_resp.json()
    assert len(schedules) == 1
    assert schedules[0]["id"] == schedule_id

    # 3. Get Specific Schedule
    get_resp = client.get(f"/api/v1/schedules/{schedule_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["search_keyword"] == "langgraph engineer"

    # 4. Update Schedule
    update_payload = {
        "execution_time": "14:00",
        "search_keyword": "langgraph and crewai",
        "selected_days": ["mon", "wed", "fri"],
    }
    put_resp = client.put(f"/api/v1/schedules/{schedule_id}", json=update_payload)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["execution_time"] == "14:00"
    assert updated_data["search_keyword"] == "langgraph and crewai"
    assert updated_data["selected_days"] == ["mon", "wed", "fri"]

    # 5. Immediate Trigger Mocking Celery Dispatch
    with patch("app.api.v1.schedules.execute_scheduled_search_and_email.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "mock-celery-task-12345"
        mock_delay.return_value = mock_task

        trigger_resp = client.post(f"/api/v1/schedules/{schedule_id}/trigger-now")
        assert trigger_resp.status_code == 200
        trigger_data = trigger_resp.json()
        assert trigger_data["task_id"] == "mock-celery-task-12345"
        assert trigger_data["schedule_id"] == schedule_id
        mock_delay.assert_called_once_with(schedule_id)

    # 6. Retrieve Execution Logs (Initially Empty)
    logs_resp = client.get(f"/api/v1/schedules/{schedule_id}/logs")
    assert logs_resp.status_code == 200
    assert isinstance(logs_resp.json(), list)

    # 7. Delete Schedule
    del_resp = client.delete(f"/api/v1/schedules/{schedule_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "SUCCESS"

    # 8. Verify 404 After Deletion
    get_after_del = client.get(f"/api/v1/schedules/{schedule_id}")
    assert get_after_del.status_code == 404


def test_repeated_task_execution_across_event_loops(monkeypatch):
    """Verify that check_and_dispatch_due_schedules runs repeatedly across multiple event loops without connection leaks."""
    import asyncio
    from contextlib import asynccontextmanager
    from sqlalchemy.pool import NullPool
    from app.tasks.pipeline_tasks import check_and_dispatch_due_schedules

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=NullPool)

    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_tables())

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def mock_get_task_db_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setattr("app.tasks.pipeline_tasks.get_task_db_session", mock_get_task_db_session)

    # Execution 1 (Loop 1)
    res1 = check_and_dispatch_due_schedules()
    assert isinstance(res1, list)

    # Execution 2 (Loop 2 - verifies no closed event loop reuse error)
    res2 = check_and_dispatch_due_schedules()
    assert isinstance(res2, list)

    # Execution 3 (Loop 3)
    res3 = check_and_dispatch_due_schedules()
    assert isinstance(res3, list)


@pytest.mark.anyio
async def test_scheduled_search_bypasses_candidate_harvesting():
    """Verify that execute_job_pipeline in scheduled pipeline task executes with harvest_candidates=False and never invokes harvester_service."""
    from unittest.mock import patch
    from app.services.pipeline_service import pipeline_runner

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    target_url = "https://www.upwork.com/jobs/~022114892483288309550"

    with patch("app.services.harvester_service.harvester_service.harvest_candidates") as mock_harvest:
        async with session_factory() as session:
            result = await pipeline_runner.execute_job_pipeline(
                job_url=target_url,
                session=session,
                auto_confirm=True,
                apply_delay=False,
                harvest_candidates=False,
            )

            assert result["status"] == "COMPLETED"
            assert "direct_search_urls" in result
            assert "linkedin_urls" in result
            assert len(result["direct_search_urls"]) > 0
            assert result["total_candidates"] == 0
            # Confirm external SerpAPI harvesting was bypassed completely
            mock_harvest.assert_not_called()


def test_zero_emoji_invariant():
    """Verify that zero emojis exist in newly added Celery, scheduling, and email code."""
    emoji_pattern = re.compile(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]"
    )

    files_to_check = [
        Path("app/models/schedule.py"),
        Path("app/models/session.py"),
        Path("app/core/celery_app.py"),
        Path("app/services/email_service.py"),
        Path("app/services/scraper_service.py"),
        Path("app/tasks/pipeline_tasks.py"),
        Path("app/schemas/schedule.py"),
        Path("app/api/v1/schedules.py"),
        Path("tests/test_celery_scheduling_email.py"),
        Path("frontend/src/components/patterns/schedule-manager-dialog.tsx"),
    ]

    for fpath in files_to_check:
        assert fpath.exists(), f"File {fpath} does not exist"
        content = fpath.read_text(encoding="utf-8")
        matches = emoji_pattern.findall(content)
        assert len(matches) == 0, f"Found emojis in {fpath}: {matches}"
