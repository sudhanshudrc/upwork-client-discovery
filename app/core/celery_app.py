import logging
from celery import Celery
from app.config import settings
from celery.signals import worker_process_init

logger = logging.getLogger("app.core.celery")

celery_app = Celery(
    "upwork_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=3600,  # 60 minutes hard timeout for sequential human scraping
    task_soft_time_limit=3300,  # 55 minutes soft timeout
    result_expires=86400,  # 24 hours
    imports=[
        "app.tasks.pipeline_tasks",
    ],
    beat_schedule={
        "check-due-schedules-poller": {
            "task": "app.tasks.pipeline_tasks.check_and_dispatch_due_schedules",
            "schedule": 60.0,  # Check every 60 seconds for due schedules
        },
    },
)


@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """
    Called when a Celery worker child process is forked.
    Disposes parent-inherited database connection pools and binds AsyncSessionLocal
    to TaskAsyncSessionLocal (NullPool) to prevent 'Event loop is closed' errors.
    """
    import app.models.session as db_session_module

    try:
        db_session_module.engine.sync_engine.dispose()
        db_session_module.task_engine.sync_engine.dispose()
    except Exception as e:
        logger.debug(f"[CELERY WORKER INIT] Parent engine pool dispose notice: {e}")

    db_session_module.AsyncSessionLocal = db_session_module.TaskAsyncSessionLocal
    logger.info("[CELERY WORKER INIT] Database sessions bound to NullPool for worker process.")


logger.info(
    f"[CELERY] Celery application initialized with broker: {settings.CELERY_BROKER_URL}"
)
