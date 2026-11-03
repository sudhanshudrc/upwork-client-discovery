// API Client for Upwork Lead Intelligence Platform
// Connects to FastAPI backend at /api/v1 (proxied to http://localhost:8000 via Vite)

export interface FeedJobItem {
  uid: string;
  title: string;
  url: string;
  budget: string | null;
  job_type?: string | null;
  experience_level: string | null;
  posted_time?: string | null;
  duration?: string | null;
  skills?: string[];
  client_spent: string | null;
  client_spent_snippet?: string | null;
  client_rating?: string | null;
  client_location?: string | null;
  client_location_snippet?: string | null;
  location?: string | null;
  proposals_tier?: string | null;
  payment_verified?: boolean;
  connects_cost?: string | null;
  badges?: string[];
  snippet: string | null;
}

export interface JobSearchResponse {
  run_id: string;
  db_run_id: string;
  query: string;
  total_extracted: number;
  snapshot_path: string;
  jobs: FeedJobItem[];
  is_cached?: boolean;
  cached_at?: string;
  expires_in_seconds?: number;
}

export interface JobDomainItem {
  query: string;
  latest_run_id: string;
  latest_run_at: string;
  total_jobs_found: number;
  total_runs_count: number;
  is_cache_active: boolean;
  expires_in_seconds: number;
  expires_in_minutes: number;
}

export interface JobDomainJobsResponse {
  query: string;
  run_id: string;
  created_at: string | null;
  total_jobs: number;
  is_cache_active: boolean;
  jobs: FeedJobItem[];
}

export interface DashboardStatsResponse {
  harvested_jobs_count: number;
  unique_domains_count: number;
  potential_clients_count: number;
  rate_limit_health: string;
  rate_limit_requests_remaining: number;
  active_session_cookies: number;
}

export interface OriginJobSummary {
  id: string;
  job_uid: string;
  title: string;
  job_url: string;
  posted_at: string | null;
}

export interface DiscoveredCandidateSummary {
  id: string;
  rank_order: number;
  full_name: string;
  headline: string | null;
  linkedin_url: string;
  match_score: number;
  tier: string;
  profile_location: string | null;
  scoring_reasons: string[] | null;
}

export interface DashboardClientItem {
  client_id: string;
  client_name: string;
  company_name: string | null;
  target_role: string | null;
  origin_job: OriginJobSummary;
  location: string;
  total_spent_usd: number;
  client_rating: string;
  total_hires: number;
  active_hires: number;
  discovered_candidates_count: number;
  tier_a_candidate: DiscoveredCandidateSummary | null;
  candidates: DiscoveredCandidateSummary[];
  direct_search_urls: string[];
}

export interface HarvestedJobItem {
  id: string;
  job_uid: string;
  title: string;
  job_url: string;
  pay_type: string;
  budget_min_usd: number | null;
  budget_max_usd: number | null;
  skills_tags: string | null;
  is_expanded: boolean;
  posted_at: string | null;
  created_at: string | null;
  client_location: string | null;
  client_total_spent: number;
  client_name: string | null;
}

export interface JobExpandResponse {
  status: string;
  job_uid: string;
  title: string;
  client_city: string | null;
  client_country: string | null;
  client_total_spent: string | null;
  total_contracts_extracted: number;
  in_progress_count: number;
  completed_count: number;
  snapshot_path: string;
}

export interface ClientProfile {
  city: string | null;
  state: string | null;
  country: string | null;
  local_time: string | null;
  total_spent_usd: string | null;
  avg_hourly_rate_usd: string | null;
  hire_rate_pct: number | null;
  total_hires: number | null;
  active_hires: number | null;
  client_rating: string | null;
  total_reviews: number | null;
  payment_verified: boolean;
  company_size: string | null;
  industry: string | null;
  member_since: string | null;
  id: string;
}

export interface ContractRecord {
  id?: string;
  contract_index?: number;
  past_title?: string;
  contract_status?: string;
  freelancer_name?: string;
  rating?: string;
  date_and_budget?: string;
  freelancer_review_clean?: string;
  client_name_mined?: string;
  excluded_client_praise?: string;

  // Compatibility aliases
  contract_title?: string;
  contract_type?: string;
  rate_or_price?: string;
  freelancer_feedback?: string;
  client_feedback?: string;
  ended_at?: string;
}

export interface ConfirmedIntelligence {
  id: string;
  job_id: string;
  confirmed_client_name: string | null;
  confirmed_client_names?: string[];
  confirmed_company_name: string | null;
  target_role: string | null;
  name_confidence: string | null;
  name_mentions_count: number;
  name_evidence_snippet: string | null;
  company_evidence_snippet: string | null;
  is_agency: boolean;
  approval_status: string;
  confirmed_at: string | null;
}

export interface JobDetailRecord {
  id: string;
  job_uid: string;
  job_url: string;
  title: string;
  pay_type: string | null;
  budget_min_usd: number | null;
  budget_max_usd: number | null;
  experience_level: string | null;
  project_duration: string | null;
  hours_per_week: string | null;
  proposals_tier: string | null;
  interviewing_count: number;
  invites_sent_count: number;
  unanswered_invites: number;
  skills_tags: string;
  description: string;
  posted_at: string | null;
  client: ClientProfile | null;
  contracts: ContractRecord[];
  intelligence: ConfirmedIntelligence | null;
  candidates?: CandidateScoreRecord[];
}

export interface EntityCandidate {
  name: string;
  confidence: string;
  source: string;
  mention_count: number;
  supporting_context: string;
}

export interface IntelligenceMiningResponse {
  job_id: string;
  job_uid: string;
  suggested_client_name: string | null;
  suggested_client_names?: string[];
  suggested_company_name: string | null;
  suggested_role: string | null;
  client_name_candidates: EntityCandidate[];
  company_candidates: EntityCandidate[];
  is_agency: boolean;
  agency_detection_reason: string;
  approval_status: string;
}

export interface CandidateScoreRecord {
  id?: string;
  job_id?: string;
  rank_order: number;
  full_name: string;
  headline: string | null;
  profile_location: string | null;
  linkedin_url: string;
  match_score: string;
  confidence: string;
  tier: string;
  is_primary_resolved: boolean;
  scoring_reasons: string[];
}

export interface DecisionMakerDiscoveryResponse {
  job_id: string;
  job_uid: string;
  client_name: string;
  location: string;
  resolved_candidate: CandidateScoreRecord | null;
  potential_candidates: CandidateScoreRecord[];
  direct_linkedin_search_urls: string[];
  excel_download_url: string;
}

export interface SessionStatusResponse {
  is_authenticated: boolean;
  session_file_exists: boolean;
  user_agent: string | null;
  rate_limit_health: string;
  message: string;
}

export interface SingleJobPipelineRequest {
  job_url: string;
  auto_confirm?: boolean;
  apply_delay?: boolean;
}

export interface SingleJobPipelineResponse {
  job_uid: string;
  job_title: string;
  job_url: string;
  client_name: string | null;
  company_name: string | null;
  total_contracts: number;
  total_candidates: number;
  primary_resolved_name: string | null;
  primary_resolved_score: string | null;
  jitter_slept_seconds: number;
  status: string;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1';

export function getStoredUserIdentifier(): string {
  return localStorage.getItem('upwork_user_identifier') || 'default';
}

export function setStoredUserIdentifier(id: string): void {
  if (id && id.trim()) {
    localStorage.setItem('upwork_user_identifier', id.trim());
  } else {
    localStorage.removeItem('upwork_user_identifier');
  }
}

export function getStoredAuthToken(): string | null {
  return localStorage.getItem('lead_intel_access_token');
}

export function setStoredAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem('lead_intel_access_token', token);
  } else {
    localStorage.removeItem('lead_intel_access_token');
  }
}

export function getStoredSerpApiKey(): string {
  return localStorage.getItem('upwork_serpapi_key') || '';
}

export function setStoredSerpApiKey(key: string): void {
  if (key && key.trim()) {
    localStorage.setItem('upwork_serpapi_key', key.trim());
  } else {
    localStorage.removeItem('upwork_serpapi_key');
  }
}

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  has_upwork_session: boolean;
  upwork_cookie_count: number;
  rate_limit_health: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfileResponse;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // User Account & Multi-Tenant Authentication
  async registerUser(payload: { email: string; password: string; full_name?: string }): Promise<AuthTokenResponse> {
    const res = await request<AuthTokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setStoredAuthToken(res.access_token);
    setStoredUserIdentifier(res.user.email);
    return res;
  },

  async loginUser(payload: { email: string; password: string }): Promise<AuthTokenResponse> {
    const res = await request<AuthTokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setStoredAuthToken(res.access_token);
    setStoredUserIdentifier(res.user.email);
    return res;
  },

  async getCurrentUser(): Promise<UserProfileResponse> {
    return request<UserProfileResponse>('/auth/me');
  },

  // Session & Authentication
  async getSessionStatus(userIdentifier?: string): Promise<SessionStatusResponse> {
    const query = userIdentifier ? `?user_identifier=${encodeURIComponent(userIdentifier)}` : '';
    return request<SessionStatusResponse>(`/auth/status${query}`);
  },

  async verifySession(userIdentifier?: string): Promise<SessionStatusResponse> {
    const query = userIdentifier ? `?user_identifier=${encodeURIComponent(userIdentifier)}` : '';
    return request<SessionStatusResponse>(`/auth/verify${query}`, { method: 'POST' });
  },

  async importSession(userIdentifier: string, sessionData: unknown, password?: string): Promise<SessionStatusResponse> {
    return request<SessionStatusResponse>('/auth/session/import', {
      method: 'POST',
      body: JSON.stringify({
        user_identifier: userIdentifier,
        session_data: sessionData,
        password: password || undefined,
      }),
    });
  },

  // Job Search Feed
  async searchJobs(query: string, limit = 5, forceLive = false): Promise<JobSearchResponse> {
    return request<JobSearchResponse>('/jobs/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit, force_live: forceLive }),
    });
  },

  // Deep Job Expansion
  async expandJob(jobUid: string, jobUrl?: string, forceLive = false): Promise<JobExpandResponse> {
    const url = jobUrl || (jobUid.startsWith('~') ? `https://www.upwork.com/jobs/${jobUid}` : `https://www.upwork.com/jobs/~02${jobUid}`);
    const query = `?job_url=${encodeURIComponent(url)}&force_live=${forceLive}`;
    return request<JobExpandResponse>(`/jobs/${encodeURIComponent(jobUid)}/expand${query}`, {
      method: 'POST',
    });
  },

  // Get Relational Job Details
  async getJob(jobUid: string): Promise<JobDetailRecord> {
    return request<JobDetailRecord>(`/jobs/${encodeURIComponent(jobUid)}`);
  },

  // Mine Intelligence (Linguistic Entity Extraction)
  async getIntelligence(jobUid: string): Promise<IntelligenceMiningResponse> {
    return request<IntelligenceMiningResponse>(`/intelligence/${encodeURIComponent(jobUid)}`);
  },

  // Human-in-the-Loop Confirmation
  async confirmIntelligence(payload: {
    job_id: string;
    confirmed_client_name: string;
    confirmed_company_name: string;
    target_role?: string;
    is_agency?: boolean;
  }): Promise<{ status: string; intelligence: ConfirmedIntelligence }> {
    return request('/intelligence/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Decision-Maker Discovery & 4-Factor Scoring
  async discoverLeads(jobUid: string): Promise<DecisionMakerDiscoveryResponse> {
    return request<DecisionMakerDiscoveryResponse>(`/leads/${encodeURIComponent(jobUid)}/discover`, {
      method: 'POST',
    });
  },

  // Autonomous Single Job Pipeline
  async runPipeline(payload: SingleJobPipelineRequest): Promise<SingleJobPipelineResponse> {
    return request<SingleJobPipelineResponse>('/pipelines/job-run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Dashboard Metrics & Drill-Down Explorers
  async getDashboardStats(): Promise<DashboardStatsResponse> {
    return request<DashboardStatsResponse>('/jobs/dashboard/stats');
  },

  async getDashboardClients(): Promise<DashboardClientItem[]> {
    return request<DashboardClientItem[]>('/jobs/dashboard/clients');
  },

  async getAllHarvestedJobs(): Promise<HarvestedJobItem[]> {
    return request<HarvestedJobItem[]>('/jobs/all');
  },

  // Search Query Domains & 1-Hour Caches
  async getDomains(): Promise<JobDomainItem[]> {
    return request<JobDomainItem[]>('/jobs/domains');
  },

  async getDomainJobs(query: string): Promise<JobDomainJobsResponse> {
    return request<JobDomainJobsResponse>(`/jobs/domains/${encodeURIComponent(query)}/jobs`);
  },

  // Excel Export URL Generator
  getExcelExportUrl(jobUid: string): string {
    return `${API_BASE}/leads/${encodeURIComponent(jobUid)}/export`;
  },

  // Batch Excel Export URL Generator (Keyword / Search Run / All Harvested Jobs)
  getBatchExcelExportUrl(query?: string, runId?: string, completedOnly = false): string {
    const params = new URLSearchParams();
    if (query && query.trim()) {
      params.set('query', query.trim());
    }
    if (runId && runId.trim()) {
      params.set('run_id', runId.trim());
    }
    if (completedOnly) {
      params.set('completed_only', 'true');
    }
    const qs = params.toString();
    return `${API_BASE}/leads/export${qs ? `?${qs}` : ''}`;
  },
};

