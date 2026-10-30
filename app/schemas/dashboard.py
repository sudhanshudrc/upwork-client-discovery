from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobDomainItem(BaseModel):
    """Summarizes a search query domain and its 1-hour cache state."""

    query: str
    latest_run_id: str
    latest_run_at: datetime
    total_jobs_found: int
    total_runs_count: int
    is_cache_active: bool
    expires_in_seconds: int
    expires_in_minutes: int


class JobDomainJobsResponse(BaseModel):
    """Returns all harvested jobs under a specific search query domain."""

    query: str
    run_id: str
    created_at: Optional[datetime] = None
    total_jobs: int
    is_cache_active: bool
    jobs: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardStatsResponse(BaseModel):
    """Consolidated 4-factor metrics for the main cockpit stat bar."""

    harvested_jobs_count: int
    unique_domains_count: int
    potential_clients_count: int
    rate_limit_health: str = "GREEN"
    rate_limit_requests_remaining: int = 45
    active_session_cookies: int = 0


class OriginJobSummary(BaseModel):
    """Job posting origin metadata for identified clients."""

    id: str
    job_uid: str
    title: str
    job_url: str
    posted_at: Optional[datetime] = None


class DiscoveredCandidateSummary(BaseModel):
    """Ranked decision-maker candidate metadata."""

    id: str
    rank_order: int
    full_name: str
    headline: Optional[str] = None
    linkedin_url: str
    match_score: float
    tier: str
    profile_location: Optional[str] = None
    scoring_reasons: Optional[List[str]] = None


class DashboardClientItem(BaseModel):
    """Potential client with mined identity, origin job, financial metrics, and discovered candidates."""

    client_id: str
    client_name: str
    company_name: Optional[str] = None
    target_role: Optional[str] = None
    origin_job: OriginJobSummary
    location: str
    total_spent_usd: float
    client_rating: str
    total_hires: int
    active_hires: int
    discovered_candidates_count: int
    tier_a_candidate: Optional[DiscoveredCandidateSummary] = None
    candidates: List[DiscoveredCandidateSummary] = Field(default_factory=list)
    direct_search_urls: List[str] = Field(default_factory=list)


class HarvestedJobItem(BaseModel):
    """Unified job listing record for the Harvested Jobs Explorer."""

    id: str
    job_uid: str
    title: str
    job_url: str
    pay_type: str
    budget_min_usd: Optional[float] = None
    budget_max_usd: Optional[float] = None
    skills_tags: Optional[str] = None
    is_expanded: bool
    posted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    client_location: Optional[str] = None
    client_total_spent: float = 0.0
    client_name: Optional[str] = None

