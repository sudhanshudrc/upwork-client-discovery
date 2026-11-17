# Backend Architecture Specification: Scheduled Human-Paced Lead Automation & Diagnostic Email Delivery

## 1. Architectural Overview & Domain Boundaries

### 1.1 Objective
Provide a robust, enterprise-grade automated lead extraction pipeline that allows users to configure recurring schedules via the frontend UI (target execution time, active days of the week, recipient email addresses, and search keywords). The backend executes searches using **strict sequential human pacing (0.5 - 2.0 min jitter)** to evade bot detection, exports a Master 34-column `.xlsx` workbook, and emails it with full diagnostic error tracking.

### 1.2 Bounded Contexts
```
[Presentation Layer (React / Vite)]
  Dialog: Schedule Manager Dialog
  API Client: Typed API Client
         |
         v
[API Gateway (FastAPI)]
  Routes: /api/v1/schedules
  Auth: Tenant Isolation
         |
         v
[Persistence Layer (PostgreSQL)]
  Tables: scheduled_keyword_searches, schedule_execution_logs, jobs
         ^
         |
[Distributed Worker (Celery & Redis)]
  Beat: Poller with SELECT ... FOR UPDATE SKIP LOCKED
  Worker: ForkPoolWorker with NullPool
  Browser: Playwright (Sequential Dwell & Viewport Scroll)
         |
         v
[Notification Subsystem]
  Excel Engine: Master 34-Column Workbook
  SMTP Delivery: Async Email with Diagnostic Logs & .xlsx
```

---

## 2. Distributed Systems & Concurrency Resilience

### 2.1 Idempotency & Race Condition Prevention
In a multi-worker Celery cluster or during concurrent poll ticks, two Beat processes or workers could attempt to dispatch the same due schedule simultaneously.
- **Architectural Solution**: Atomic row locking via PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`.
```python
stmt = (
    select(ScheduledKeywordSearch)
    .where(
        ScheduledKeywordSearch.is_active == True,
        or_(
            ScheduledKeywordSearch.next_run_at <= now_utc,
            ScheduledKeywordSearch.next_run_at.is_(None),
        ),
    )
    .with_for_update(skip_locked=True)
    .order_by(ScheduledKeywordSearch.created_at.asc())
)
```
- **Guarantee**: If Worker A acquires the row lock, it dispatches the Celery task, immediately updates `next_run_at` to the future date, and commits. Worker B skips locked rows, completely eliminating duplicate task dispatching.

### 2.2 Task Queue & Workload Isolation
Sequential scraping of 10 jobs with 30s-120s delays takes **10 to 25 minutes**:
- **Risk**: Long-running scraping tasks can saturate the worker pool, blocking short API operations (like on-demand status probes or instant triggers).
- **Architectural Solution**:
  - `acks_late = True`: Tasks are acknowledged only upon completion, preventing silent task loss if a container restarts mid-scrape.
  - `task_reject_on_worker_lost = True`: Re-queues tasks if a worker process terminates unexpectedly.
  - Prefetch Multiplier set to `1`: Prevents a single worker process from hoarding multiple long-running tasks.
  - Timeouts: Hard limit `task_time_limit = 3600` (60 min), Soft limit `task_soft_time_limit = 3300` (55 min).

### 2.3 Database Session Lifecycle in Celery (`NullPool`)
As established in root-cause remediation:
- Background tasks run via `asyncio.run()`, which creates and closes an event loop per task.
- Celery worker must strictly use on-demand sessions via `get_task_db_session()` backed by `poolclass=NullPool`.
- Every checkout opens a fresh connection on the active loop; every check-in closes it immediately. Engine disposal occurs in the `finally:` block. No stale connection pooling across loops or forks.

---

## 3. Data Contract & Domain Schema

### 3.1 PostgreSQL Schema (`app/models/schedule.py`)
```python
class ScheduledKeywordSearch(Base):
    __tablename__ = "scheduled_keyword_searches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    search_keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    target_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Schedule Configuration
    frequency_type: Mapped[str] = mapped_column(String(20), default="CRON", nullable=False)
    execution_time: Mapped[str] = mapped_column(String(10), default="10:30", nullable=False)
    selected_days: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)  # ["wed", "thu", "fri", "sat", "sun"]
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Anti-Bot Pacing Bounds (Seconds)
    min_delay_seconds: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    max_delay_seconds: Mapped[float] = mapped_column(Float, default=120.0, nullable=False)

    # Notifications
    recipient_emails: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    email_subject_template: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Lifecycle State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
```

### 3.2 Timezone-Aware Next-Run Calculation (`calculate_next_run_at`)
Using Python's standard `zoneinfo.ZoneInfo`:
1. Parse `execution_time` (`HH:mm`) in the target `timezone` (e.g. `Asia/Kolkata`).
2. Starting from the reference timestamp, evaluate candidate days in order (today, +1 day, +2 days...).
3. Check if candidate day matches `selected_days` (e.g. `wed`, `thu`, `fri`, `sat`, `sun`).
4. If candidate day matches and candidate time is in the future:
   - Convert candidate local `datetime` to UTC.
   - Return as timezone-aware UTC `datetime`.

---

## 4. Anti-Bot Human Dwell Pacing Engine

### 4.1 Strict Sequential Processing Pipeline
In `_async_execute_scheduled_search`:
```python
captured_errors: List[Dict[str, Any]] = []

for idx, item in enumerate(jobs_to_expand, 1):
    job_url = item.get("job_url") or item.get("url")
    if not job_url:
        continue

    # 1. Randomized Human Jitter Delay (0.5 - 2.0 min)
    if idx > 1:
        delay = random.uniform(sched.min_delay_seconds, sched.max_delay_seconds)
        logger.info(
            f"[HUMAN JITTER] Pausing {delay:.1f}s before inspecting job {idx}/{len(jobs_to_expand)} to emulate human reading behavior..."
        )
        await asyncio.sleep(delay)

    # 2. Resilient Execution with Error Capture
    try:
        await pipeline_runner.execute_job_pipeline(
            job_url=job_url,
            session=session,
            auto_confirm=True,
            apply_delay=True,
            user_identifier=user_identifier,
        )
        expanded_count += 1
        # Commit progress immediately after each job
        await session.commit()
    except Exception as job_err:
        await session.rollback()
        logger.warning(f"[CELERY] [JOB ERROR] Failure expanding job {job_url}: {job_err}", exc_info=True)
        captured_errors.append({
            "job_url": job_url,
            "job_index": idx,
            "error_type": type(job_err).__name__,
            "message": str(job_err),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
```

### 4.2 Playwright Micro-Interactions
- Smooth variable scroll down (300px - 700px).
- Reading dwell pause (3s - 7s) on contract history elements.
- Gentle scroll up (100px - 200px) before final extraction.

---

## 5. Diagnostic Email Reporting & Partial Data Resilience

### 5.1 Partial Data Guarantee
If an unrecoverable error occurs (e.g., Upwork logs out after job 5 of 10):
- The 5 harvested jobs already committed to PostgreSQL are exported to the Master 34-column `.xlsx` file.
- The user is **never** left with an empty inbox or lost work.

### 5.2 Diagnostic Error Presentation
In `email_service.send_excel_report_email_async`:
- **When Clean**: Standard executive summary card + top 5 lead highlights table + `.xlsx` attachment.
- **When Partial Errors Occurred**:
  - Adds an amber warning alert in the email body detailing the failed job URLs and error causes.
  - Generates and attaches `pipeline_execution_errors.log` containing formatted stack traces alongside the `.xlsx` workbook.
- **When Entire Search Failed**:
  - Sends diagnostic alert email explaining the exact blocker (e.g. "Cloudflare Turnstile challenge active; cookies require renewal via scripts/interactive_login.py").

---

## 6. Frontend UI Specification

### 6.1 Schedule Manager Component (`frontend/src/components/patterns/schedule-manager-dialog.tsx`)
- **State**:
  - `keyword`: string (default active search keyword).
  - `selectedDays`: string[] (empty by default `[]`; no days pre-selected; user explicitly selects the active days; validation requires at least 1 day before saving).
  - `time`: string (default `"10:30"`).
  - `timezone`: string (detected from browser `Intl.DateTimeFormat().resolvedOptions().timeZone`, default `"Asia/Kolkata"`).
  - `recipientEmails`: string[] (tag input with validation).
  - `targetLimit`: number (default `10`).
- **Interactive Controls**:
  - 7 multi-select pill buttons: `[Mon] [Tue] [Wed] [Thu] [Fri] [Sat] [Sun]` (all unselected by default; user clicks to toggle active days).
  - HTML5 Time picker: `<input type="time" value={time} onChange={...} />`.
  - Multi-email chip list with inline addition (`Enter` key) and deletion (`x` button).
  - Existing schedules management table with Next Run time, `Run Now`, `Edit`, `Pause`, `Delete` actions.

---

## 7. Step-by-Step Implementation Roadmap

### Phase 1: Database Model & Schema Update
- Add `execution_time`, `selected_days`, `timezone`, `min_delay_seconds`, `max_delay_seconds` to `ScheduledKeywordSearch`.
- Update Pydantic schemas in `app/schemas/schedule.py`.
- Ensure `init_db()` synchronizes any missing columns cleanly.

### Phase 2: Next-Run Calculation with Timezones
- Implement `calculate_next_run_at()` using `zoneinfo.ZoneInfo`.
- Add unit tests verifying:
  - Monday/Tuesday correctly roll forward to Wednesday 10:30 AM.
  - Sunday after 10:30 AM rolls forward to Wednesday 10:30 AM.
  - Correct UTC conversion across daylight saving / standard time.

### Phase 3: Celery Sequential Jitter & Row-Locking
- Add `with_for_update(skip_locked=True)` in `_async_check_and_dispatch_due_schedules`.
- Implement human delay loop (`random.uniform(min_delay, max_delay)`) and intermediate DB commits in `_async_execute_scheduled_search`.
- Implement in-memory `captured_errors` ledger.

### Phase 4: Diagnostic Email Reporting
- Update `email_service.send_excel_report_email_async` to accept `error_logs`.
- Build HTML warning card and `.log` file attachment generator.

### Phase 5: Frontend UI
- Build `schedule-manager-dialog.tsx`.
- Connect to API client in `frontend/src/services/api.ts`.
- Integrate modal toggle into `app-header.tsx`.

### Phase 6: Automated Verification & Invariants
- Unit tests in `tests/test_celery_scheduling_email.py`.
- Enforce strict zero-emoji invariant across all code and logs (`GEMINI.md`).
- Enforce standard bracketed logging tags: `[SCHEDULER]`, `[HUMAN JITTER]`, `[EMAIL]`.
