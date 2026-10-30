from app.schemas.auth import UpworkCredentialsCreate, SessionStatusResponse
from app.schemas.client import ClientBase, ClientCreate, ClientResponse
from app.schemas.history import (
    ContractHistoryBase,
    ContractHistoryCreate,
    ContractHistoryResponse,
)
from app.schemas.intelligence import (
    DiscoveredEntityItem,
    IntelligenceExtractionResponse,
    UserConfirmationRequest,
    ClientIntelligenceResponse,
)
from app.schemas.candidate import (
    CandidateBase,
    CandidateCreate,
    CandidateResponse,
    LeadDiscoveryResultResponse,
)
from app.schemas.job import (
    JobSearchQuery,
    JobBase,
    JobCreate,
    JobSummaryResponse,
    JobDetailResponse,
)
from app.schemas.dashboard import (
    JobDomainItem,
    JobDomainJobsResponse,
    DashboardStatsResponse,
    OriginJobSummary,
    DiscoveredCandidateSummary,
    DashboardClientItem,
    HarvestedJobItem,
)

__all__ = [
    "UpworkCredentialsCreate",
    "SessionStatusResponse",
    "ClientBase",
    "ClientCreate",
    "ClientResponse",
    "ContractHistoryBase",
    "ContractHistoryCreate",
    "ContractHistoryResponse",
    "DiscoveredEntityItem",
    "IntelligenceExtractionResponse",
    "UserConfirmationRequest",
    "ClientIntelligenceResponse",
    "CandidateBase",
    "CandidateCreate",
    "CandidateResponse",
    "LeadDiscoveryResultResponse",
    "JobSearchQuery",
    "JobBase",
    "JobCreate",
    "JobSummaryResponse",
    "JobDetailResponse",
    "JobDomainItem",
    "JobDomainJobsResponse",
    "DashboardStatsResponse",
    "OriginJobSummary",
    "DiscoveredCandidateSummary",
    "DashboardClientItem",
    "HarvestedJobItem",
]

