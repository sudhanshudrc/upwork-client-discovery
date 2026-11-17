from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ScheduleCreateRequest(BaseModel):
    """Payload to create a new scheduled keyword search and email dispatch rule."""

    search_keyword: str = Field(..., min_length=1, max_length=100, description="Upwork search query keyword")
    target_limit: int = Field(default=10, ge=1, le=100, description="Number of top feed jobs to retrieve")
    frequency_type: str = Field(default="CRON", description="'CRON' or 'INTERVAL'")
    execution_time: str = Field(default="10:30", pattern=r"^\d{2}:\d{2}$", description="Local execution time in HH:mm format")
    selected_days: List[str] = Field(default_factory=list, description="Active days of week e.g. ['wed', 'thu', 'fri', 'sat', 'sun']")
    timezone: str = Field(default="Asia/Kolkata", max_length=50, description="IANA timezone name e.g. Asia/Kolkata")
    interval_hours: Optional[int] = Field(default=6, ge=1, le=168, description="Execution interval in hours if INTERVAL frequency")
    cron_expression: Optional[str] = Field(default=None, max_length=50, description="Optional cron expression")
    min_delay_seconds: float = Field(default=30.0, ge=5.0, le=600.0, description="Minimum human jitter sleep between jobs")
    max_delay_seconds: float = Field(default=120.0, ge=5.0, le=600.0, description="Maximum human jitter sleep between jobs")
    recipient_emails: List[EmailStr] = Field(..., min_length=1, description="Notification email recipient list")
    email_subject_template: Optional[str] = Field(default=None, max_length=255, description="Custom subject template")
    is_active: bool = Field(default=True, description="Whether the schedule is active")


class ScheduleUpdateRequest(BaseModel):
    """Payload to update an existing scheduled keyword search rule."""

    search_keyword: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_limit: Optional[int] = Field(default=None, ge=1, le=100)
    frequency_type: Optional[str] = Field(default=None)
    execution_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    selected_days: Optional[List[str]] = Field(default=None)
    timezone: Optional[str] = Field(default=None, max_length=50)
    interval_hours: Optional[int] = Field(default=None, ge=1, le=168)
    cron_expression: Optional[str] = Field(default=None, max_length=50)
    min_delay_seconds: Optional[float] = Field(default=None, ge=5.0, le=600.0)
    max_delay_seconds: Optional[float] = Field(default=None, ge=5.0, le=600.0)
    recipient_emails: Optional[List[EmailStr]] = Field(default=None)
    email_subject_template: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = Field(default=None)


class ScheduleExecutionLogResponse(BaseModel):
    """Execution audit trail log entry for a scheduled run."""

    id: str
    schedule_id: str
    status: str
    jobs_scraped: int
    jobs_expanded: int
    excel_file_path: Optional[str] = None
    email_status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleResponse(BaseModel):
    """Representation of an active or inactive keyword schedule."""

    id: str
    user_identifier: str
    search_keyword: str
    target_limit: int
    frequency_type: str
    execution_time: str = "10:30"
    selected_days: List[str] = Field(default_factory=list)
    timezone: str = "Asia/Kolkata"
    interval_hours: Optional[int] = None
    cron_expression: Optional[str] = None
    min_delay_seconds: float = 30.0
    max_delay_seconds: float = 120.0
    recipient_emails: List[str]
    email_subject_template: Optional[str] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    latest_execution: Optional[ScheduleExecutionLogResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleTriggerResponse(BaseModel):
    """Immediate execution trigger confirmation."""

    message: str
    task_id: str
    schedule_id: str
