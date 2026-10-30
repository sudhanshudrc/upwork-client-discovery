import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  ExternalLink,
  Moon,
  Sun,
  RefreshCw,
  UserCheck,
  AlertTriangle,
  KeyRound,
  Filter,
  MapPin,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';

// Composed UI Patterns (/ui-pattern)
import { SessionStatusBadge } from '@/components/patterns/session-status-badge';
import { StatGrid } from '@/components/patterns/stat-grid';
import { SearchHeader } from '@/components/patterns/search-header';
import { JobFeedTable } from '@/components/patterns/job-feed-table';
import { ContractHistoryCard } from '@/components/patterns/contract-history-card';
import { CandidateRankingCard } from '@/components/patterns/candidate-ranking-card';
import { HitlReviewDialog } from '@/components/patterns/hitl-review-dialog';
import { SessionImportDialog } from '@/components/patterns/session-import-dialog';
import { PipelineProgressBar } from '@/components/patterns/pipeline-progress-bar';
import { IntelligenceCard } from '@/components/patterns/intelligence-card';
import { HarvestedJobsModal } from '@/components/patterns/harvested-jobs-modal';
import { JobDomainsModal } from '@/components/patterns/job-domains-modal';
import { PotentialClientsModal } from '@/components/patterns/potential-clients-modal';
import { SearchDomainBar } from '@/components/patterns/search-domain-bar';

// Typed Hooks
import { useSessionStatus } from '@/hooks/use-session';
import { useJobSearch, useJobDetails, useExpandJob } from '@/hooks/use-jobs';
import { useIntelligence, useConfirmIntelligence } from '@/hooks/use-intelligence';
import { useDiscoverLeads } from '@/hooks/use-leads';
import { useRunSinglePipeline } from '@/hooks/use-pipeline';
import { useDashboardStats } from '@/hooks/use-dashboard';
import { useDomains } from '@/hooks/use-domains';
import type { FeedJobItem, DecisionMakerDiscoveryResponse, SessionStatusResponse } from '@/services/api';

function cleanBudget(raw?: string | null): string {
  if (!raw) return 'Not specified';
  const lower = raw.toLowerCase();
  if (lower.includes('connect_jobtypes') || lower.includes('hourlyrange') || lower.includes('hourly')) {
    const match = raw.match(/\$\d+(?:\.\d+)?(?:\s*-\s*\$\d+(?:\.\d+)?)?/);
    return match ? match[0] : 'Hourly';
  }
  if (lower.includes('fixed')) {
    const match = raw.match(/\$\d+(?:\.\d+)?/);
    return match ? match[0] : 'Fixed Price';
  }
  return raw;
}

function cleanExperienceLevel(raw?: string | null): string {
  if (!raw) return 'Any Experience';
  const lower = raw.toLowerCase();
  if (lower.includes('intermediate')) return 'Intermediate';
  if (lower.includes('expert')) return 'Expert';
  if (lower.includes('entry')) return 'Entry Level';
  if (raw.includes('_')) {
    const cleaned = raw.replace(/^[0-9a-zA-Z]+_/, '').replace(/_[0-9a-zA-Z]+$/, '');
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }
  return raw;
}

export function App() {
  const [isDarkMode, setIsDarkMode] = React.useState(false);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = React.useState('Frontend Developer');
  const [limit, setLimit] = React.useState(3);
  const [forceLive, setForceLive] = React.useState(false);
  const [feedFilterText, setFeedFilterText] = React.useState('');
  const [jobs, setJobs] = React.useState<FeedJobItem[]>([]);
  const [selectedJobUid, setSelectedJobUid] = React.useState<string | null>(null);

  // Dialog States
  const [isHitlDialogOpen, setIsHitlDialogOpen] = React.useState(false);
  const [isSessionDialogOpen, setIsSessionDialogOpen] = React.useState(false);
  const [isHarvestedJobsModalOpen, setIsHarvestedJobsModalOpen] = React.useState(false);
  const [isJobDomainsModalOpen, setIsJobDomainsModalOpen] = React.useState(false);
  const [isPotentialClientsModalOpen, setIsPotentialClientsModalOpen] = React.useState(false);

  // HITL Form State
  const [hitlClientName, setHitlClientName] = React.useState('');
  const [hitlCompanyName, setHitlCompanyName] = React.useState('');
  const [hitlRole, setHitlRole] = React.useState('CTO');
  const [discoveryResult, setDiscoveryResult] = React.useState<DecisionMakerDiscoveryResponse | null>(null);
  const [activeTab, setActiveTab] = React.useState<string>('intelligence');
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [showPipelineProgress, setShowPipelineProgress] = React.useState(false);

  // TanStack Query Hooks
  const queryClient = useQueryClient();
  const { data: sessionStatus, isLoading: isLoadingSession, refetch: refetchSession } = useSessionStatus();
  const searchMutation = useJobSearch();
  const expandMutation = useExpandJob();
  const confirmMutation = useConfirmIntelligence();
  const discoverMutation = useDiscoverLeads();
  const pipelineMutation = useRunSinglePipeline();

  const { data: dashboardStats } = useDashboardStats();
  const { data: domainList } = useDomains();

  const { data: selectedJob, isLoading: isLoadingJobDetail } = useJobDetails(selectedJobUid);
  const { data: intelligence } = useIntelligence(selectedJobUid);

  // Dark Mode Toggle
  const toggleDarkMode = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return next;
    });
  };

  // Sync HITL fields when intelligence data loads
  React.useEffect(() => {
    if (intelligence) {
      if (intelligence.suggested_client_name) setHitlClientName(intelligence.suggested_client_name);
      if (intelligence.suggested_company_name) setHitlCompanyName(intelligence.suggested_company_name);
      if (intelligence.suggested_role) setHitlRole(intelligence.suggested_role);
    }
  }, [intelligence]);

  // Search Jobs Feed
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);

    searchMutation.mutate(
      { query: searchQuery, limit, forceLive },
      {
        onSuccess: (data) => {
          setJobs(data.jobs);
          if (data.jobs.length > 0) {
            setSelectedJobUid(data.jobs[0].uid);
          }
        },
        onError: (err) => {
          setErrorMessage(err.message || 'Job search failed');
        },
      }
    );
  };

  // Select Domain Keyword (Hits 1-hour cache or fetches from DB)
  const handleSelectDomain = (domainQuery: string) => {
    setSearchQuery(domainQuery);
    setErrorMessage(null);
    searchMutation.mutate(
      { query: domainQuery, limit, forceLive: false },
      {
        onSuccess: (data) => {
          setJobs(data.jobs);
          if (data.jobs.length > 0) {
            setSelectedJobUid(data.jobs[0].uid);
          }
        },
        onError: (err) => {
          setErrorMessage(err.message || 'Failed to load jobs for domain');
        },
      }
    );
  };

  // Load Domain Extracted Jobs directly into Cockpit feed
  const handleLoadDomainJobs = (domainQuery: string, extractedJobs: FeedJobItem[]) => {
    setSearchQuery(domainQuery);
    setJobs(extractedJobs);
    if (extractedJobs.length > 0) {
      setSelectedJobUid(extractedJobs[0].uid);
    }
  };

  const currentFeedJob = React.useMemo(() => {
    return jobs.find((j) => j.uid === selectedJobUid) || null;
  }, [jobs, selectedJobUid]);

  // Expand Contract History
  const handleExpandContracts = () => {
    if (!selectedJobUid) return;
    setErrorMessage(null);

    expandMutation.mutate(
      {
        jobUid: selectedJobUid,
        jobUrl: currentFeedJob?.url,
        forceLive,
      },
      {
        onError: (err) => {
          setErrorMessage(err.message || 'Contract expansion failed');
        },
      }
    );
  };

  // Open HITL Review Dialog
  const handleOpenHitl = () => {
    if (intelligence) {
      setHitlClientName(intelligence.suggested_client_name || '');
      setHitlCompanyName(intelligence.suggested_company_name || '');
      setHitlRole(intelligence.suggested_role || 'CTO');
    }
    setIsHitlDialogOpen(true);
  };

  // Direct Decision-Maker Discovery Trigger
  const handleDirectDiscover = (targetUid?: string) => {
    const uid = targetUid || selectedJobUid;
    if (!uid) return;
    setErrorMessage(null);
    setActiveTab('candidates'); // Instantly navigate user to Decision-Makers tab

    discoverMutation.mutate(uid, {
      onSuccess: (leads) => {
        setDiscoveryResult(leads);
        queryClient.invalidateQueries({ queryKey: ['job-details', uid] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
      },
      onError: (err) => {
        setErrorMessage(err.message || 'Lead discovery failed');
      },
    });
  };

  // Confirm Entity & Trigger Lead Discovery
  const handleConfirmAndDiscover = () => {
    const jobId = selectedJob?.id;
    if (!jobId || !selectedJobUid) return;
    setErrorMessage(null);

    const clientName =
      hitlClientName.trim() ||
      selectedJob.intelligence?.confirmed_client_name ||
      intelligence?.suggested_client_name ||
      'Client';

    confirmMutation.mutate(
      {
        job_id: jobId,
        job_uid: selectedJobUid,
        confirmed_client_name: clientName,
        confirmed_company_name: hitlCompanyName.trim() || selectedJob.intelligence?.confirmed_company_name || '',
        target_role: hitlRole.trim() || selectedJob.intelligence?.target_role || 'CTO',
        is_agency: intelligence?.is_agency || false,
      },
      {
        onSuccess: () => {
          setIsHitlDialogOpen(false);
          handleDirectDiscover(selectedJobUid);
        },
        onError: (err) => {
          setErrorMessage(err.message || 'Entity confirmation failed');
        },
      }
    );
  };

  // Run Autonomous Single-Job Pipeline
  const handleRunPipeline = () => {
    const targetUrl = selectedJob?.job_url || currentFeedJob?.url;
    if (!targetUrl) return;
    setErrorMessage(null);
    setShowPipelineProgress(true);
    setActiveTab('candidates');

    pipelineMutation.mutate(
      {
        job_url: targetUrl,
        auto_confirm: true,
        apply_delay: false,
      },
      {
        onSuccess: (pipelineRes) => {
          discoverMutation.mutate(pipelineRes.job_uid, {
            onSuccess: (leads) => {
              setDiscoveryResult(leads);
              queryClient.invalidateQueries({ queryKey: ['job-details', pipelineRes.job_uid] });
              queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
              queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
            },
          });
        },
        onError: (err) => {
          setErrorMessage(err.message || 'Autonomous pipeline execution failed');
        },
      }
    );
  };

  // Effective decision-maker discovery data: Prioritizes active query result, falls back to loaded DB candidates
  const effectiveDiscoveryData = React.useMemo<DecisionMakerDiscoveryResponse | null>(() => {
    if (discoveryResult && discoveryResult.job_uid === selectedJobUid) {
      return discoveryResult;
    }
    if (selectedJob && selectedJob.candidates && selectedJob.candidates.length > 0) {
      const candidates = [...selectedJob.candidates].sort((a, b) => a.rank_order - b.rank_order);
      const primary = candidates.find((c) => c.is_primary_resolved || Number(c.match_score) >= 70) || null;
      const potential = candidates.filter((c) => c !== primary);
      const clientName =
        selectedJob.intelligence?.confirmed_client_name ||
        intelligence?.suggested_client_name ||
        'Client';
      const city = selectedJob.client?.city || '';
      const country = selectedJob.client?.country || '';
      const location = city && country ? `${city}, ${country}` : city || country || 'Worldwide';

      return {
        job_id: selectedJob.id,
        job_uid: selectedJob.job_uid,
        client_name: clientName,
        location,
        resolved_candidate: primary,
        potential_candidates: potential.length > 0 ? potential : (primary ? [] : candidates),
        direct_linkedin_search_urls: [
          `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(clientName)}&origin=FACETED_SEARCH`,
          ...(city ? [`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${clientName} ${city}`)}&origin=FACETED_SEARCH`] : []),
          ...(country ? [`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${clientName} ${country}`)}&origin=FACETED_SEARCH`] : []),
          `https://www.google.com/search?q=site%3Alinkedin.com/in/%20%22${encodeURIComponent(clientName)}%22`,
        ],
        excel_download_url: `/api/v1/leads/${selectedJob.job_uid}/export`,
      };
    }
    return null;
  }, [discoveryResult, selectedJob, selectedJobUid]);

  const candidatesCount =
    (effectiveDiscoveryData?.resolved_candidate ? 1 : 0) +
    (effectiveDiscoveryData?.potential_candidates?.length || 0);

  // Filter jobs client-side
  const filteredJobs = React.useMemo(() => {
    if (!feedFilterText.trim()) return jobs;
    const lower = feedFilterText.toLowerCase();
    return jobs.filter(
      (j) =>
        j.title.toLowerCase().includes(lower) ||
        (j.snippet && j.snippet.toLowerCase().includes(lower)) ||
        j.uid.includes(lower)
    );
  }, [jobs, feedFilterText]);

  return (
    <div className="min-h-screen bg-[#F8F9F3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] transition-colors duration-200">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-[#E1E4D3] dark:border-[#2E331E] bg-white/95 dark:bg-[#202414]/95 backdrop-blur-sm shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="size-9 rounded-lg bg-[#636B2F] flex items-center justify-center text-[#F8F9F3] font-bold text-sm tracking-wide">
              LI
            </div>
            <div>
              <div className="font-semibold text-sm tracking-tight text-[#3D4127] dark:text-[#F8F9F3]">
                Lead Intelligence Cockpit
              </div>
              <div className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
                Client Discovery & Decision-Maker Finder
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SessionStatusBadge status={sessionStatus} isLoading={isLoadingSession} />

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsSessionDialogOpen(true)}
              className="text-xs"
            >
              <KeyRound className="size-3.5 me-1.5 text-[#636B2F]" />
              Cookies
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={toggleDarkMode}
              title="Toggle Theme"
            >
              {isDarkMode ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Error Alert Display */}
        {errorMessage && (
          <div className="rounded-lg border border-[#A33B3B]/30 bg-[#FDF2F2] dark:bg-[#3D1414] p-4 text-xs text-[#A33B3B] dark:text-[#F3C4C4] flex items-center gap-2">
            <AlertTriangle className="size-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Global KPI Stat Grid */}
        <StatGrid
          harvestedJobsCount={dashboardStats?.harvested_jobs_count ?? jobs.length}
          uniqueDomainsCount={dashboardStats?.unique_domains_count ?? (domainList?.length || 0)}
          potentialClientsCount={dashboardStats?.potential_clients_count ?? 0}
          rateLimitHealth={dashboardStats?.rate_limit_health || sessionStatus?.rate_limit_health || 'GREEN'}
          activeCookiesCount={dashboardStats?.active_session_cookies || (sessionStatus?.is_authenticated ? 79 : 0)}
          latestDomain={domainList?.[0]?.query || searchQuery}
          onOpenHarvestedJobs={() => setIsHarvestedJobsModalOpen(true)}
          onOpenJobDomains={() => setIsJobDomainsModalOpen(true)}
          onOpenPotentialClients={() => setIsPotentialClientsModalOpen(true)}
          onOpenSessionHealth={() => setIsSessionDialogOpen(true)}
        />

        {/* Pipeline Execution Stages Progress */}
        {showPipelineProgress && (
          <PipelineProgressBar isRunning={pipelineMutation.isPending} />
        )}

        {/* Search Header Pattern */}
        <SearchHeader
          query={searchQuery}
          onQueryChange={setSearchQuery}
          limit={limit}
          onLimitChange={setLimit}
          forceLive={forceLive}
          onForceLiveChange={setForceLive}
          onSearch={handleSearch}
          isSearching={searchMutation.isPending}
          onRunSinglePipeline={handleRunPipeline}
          isRunningPipeline={pipelineMutation.isPending}
          hasSelectedJob={Boolean(selectedJob)}
        />

        {/* Search Keyword Domains Pill Bar */}
        <SearchDomainBar
          domains={domainList}
          activeQuery={searchQuery}
          onSelectDomain={handleSelectDomain}
          onOpenDomainsModal={() => setIsJobDomainsModalOpen(true)}
        />

        {/* Two-Pane Cockpit */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Pane: Job Feed Listing (4 columns) */}
          <div className="lg:col-span-4 space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#656C43] dark:text-[#BAC095]">
                Found Jobs ({filteredJobs.length})
              </span>
              <div className="flex items-center gap-1.5 text-xs text-[#656C43] dark:text-[#BAC095]">
                <Filter className="size-3 text-[#636B2F]" />
                <input
                  type="text"
                  value={feedFilterText}
                  onChange={(e) => setFeedFilterText(e.target.value)}
                  placeholder="Filter list..."
                  className="w-24 px-1.5 py-0.5 text-[11px] rounded border border-[#BAC095] dark:border-[#4A5129] bg-transparent outline-none focus:border-[#636B2F]"
                />
              </div>
            </div>

            <JobFeedTable
              jobs={filteredJobs}
              selectedJobUid={selectedJobUid}
              onSelectJob={(uid) => setSelectedJobUid(uid)}
              onInitialSearch={() => handleSearch()}
            />
          </div>

          {/* Right Pane: Deep Inspector & Scored Candidates (8 columns) */}
          <div className="lg:col-span-8 space-y-4">
            {isLoadingJobDetail ? (
              <Card className="p-6 space-y-4">
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-32 w-full" />
              </Card>
            ) : selectedJob ? (
              <Card>
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base text-[#3D4127] dark:text-[#F8F9F3]">{selectedJob.title}</CardTitle>
                        <a
                          href={selectedJob.job_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#636B2F] hover:text-[#3D4127] dark:text-[#D4DE95] transition-colors"
                          title="Open on Upwork"
                        >
                          <ExternalLink className="size-4" />
                        </a>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <CardDescription className="font-mono text-[11px] text-[#656C43] dark:text-[#BAC095]">
                          Job ID: {selectedJob.job_uid.slice(-8)}
                        </CardDescription>

                        {(selectedJob.client?.city || selectedJob.client?.country || currentFeedJob?.client_location || currentFeedJob?.client_location_snippet) && (
                          <Badge variant="neutral" className="text-[10px] flex items-center gap-1 font-medium text-[#636B2F] dark:text-[#D4DE95]">
                            <MapPin className="size-3" />
                            {selectedJob.client?.city && selectedJob.client?.country
                              ? `${selectedJob.client.city}, ${selectedJob.client.country}`
                              : selectedJob.client?.country || currentFeedJob?.client_location || currentFeedJob?.client_location_snippet}
                          </Badge>
                        )}

                        {(selectedJob.intelligence?.confirmed_client_name || intelligence?.suggested_client_name) && (
                          <Badge variant="brand" className="text-[10px]">
                            Client: {selectedJob.intelligence?.confirmed_client_name || intelligence?.suggested_client_name}
                          </Badge>
                        )}

                        {(selectedJob.intelligence?.confirmed_company_name || intelligence?.suggested_company_name) && (
                          <Badge variant="neutral" className="text-[10px]">
                            Company: {selectedJob.intelligence?.confirmed_company_name || intelligence?.suggested_company_name}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleExpandContracts}
                        disabled={expandMutation.isPending}
                      >
                        {expandMutation.isPending ? (
                          <RefreshCw className="size-3.5 me-1 animate-spin" />
                        ) : null}
                        Fetch History ({selectedJob.contracts?.length || 0})
                      </Button>

                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleOpenHitl}
                      >
                        <UserCheck className="size-3.5 me-1" />
                        Verify Client Details
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-5">
                  {/* Client Summary Metric Bar */}
                  {selectedJob.client && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-lg bg-[#EFF2E3] dark:bg-[#15180E] border border-[#E1E4D3] dark:border-[#2E331E]">
                      <div>
                        <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Total Spend</div>
                        <div className="text-sm font-semibold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
                          ${Number(selectedJob.client.total_spent_usd || 0).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Hires / Active</div>
                        <div className="text-sm font-semibold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
                          {selectedJob.client.total_hires || 0} / {selectedJob.client.active_hires || 0}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Avg Hourly Rate</div>
                        <div className="text-sm font-semibold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
                          ${selectedJob.client.avg_hourly_rate_usd || '0.00'} / hr
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Payment Status</div>
                        <div className="text-sm font-semibold text-[#636B2F] dark:text-[#D4DE95]">
                          {selectedJob.client.payment_verified ? 'Verified' : 'Unverified'}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Multi-Tab Deep Inspector */}
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid grid-cols-4 w-full">
                      <TabsTrigger value="intelligence" className="truncate">
                        Client Profile
                      </TabsTrigger>
                      <TabsTrigger value="contracts" className="truncate">
                        Past Contracts ({selectedJob.contracts?.length || 0})
                      </TabsTrigger>
                      <TabsTrigger value="candidates" className="truncate flex items-center justify-center gap-1.5">
                        <span>Decision-Makers</span>
                        {candidatesCount > 0 && (
                          <Badge variant="brand" className="px-1.5 py-0 text-[10px] leading-tight">
                            {candidatesCount}
                          </Badge>
                        )}
                      </TabsTrigger>
                      <TabsTrigger value="description" className="truncate">
                        Job Details
                      </TabsTrigger>
                    </TabsList>

                    <div className="min-h-[440px]">
                      {/* Tab 1: Client Profile Entity Card */}
                      <TabsContent value="intelligence" className="pt-2 min-h-[440px]">
                        <IntelligenceCard
                          intelligence={intelligence || null}
                          confirmedIntelligence={selectedJob.intelligence || null}
                          clientLocation={
                            selectedJob.client?.city && selectedJob.client?.country
                              ? `${selectedJob.client.city}, ${selectedJob.client.country}`
                              : selectedJob.client?.country || currentFeedJob?.client_location || currentFeedJob?.client_location_snippet || null
                          }
                          onOpenReviewDialog={handleOpenHitl}
                          onDiscoverLeads={() => handleDirectDiscover(selectedJob.job_uid)}
                          isDiscovering={confirmMutation.isPending || discoverMutation.isPending}
                        />
                      </TabsContent>

                      {/* Tab 2: Contract History Card */}
                      <TabsContent value="contracts" className="pt-2 min-h-[440px]">
                        <ContractHistoryCard contracts={selectedJob.contracts} />
                      </TabsContent>

                      {/* Tab 3: Decision-Makers Candidate Ranking Card */}
                      <TabsContent value="candidates" className="pt-2 min-h-[440px]">
                        <CandidateRankingCard
                          discoveryData={effectiveDiscoveryData}
                          jobUid={selectedJob.job_uid}
                          onMineIntelligence={() => handleDirectDiscover(selectedJob.job_uid)}
                          isLoading={discoverMutation.isPending}
                        />
                      </TabsContent>

                      {/* Tab 4: Job Description */}
                      <TabsContent value="description" className="pt-2 min-h-[440px]">
                        <p className="text-xs text-[#2C5756] dark:text-[#C2D7CD] leading-relaxed whitespace-pre-line p-3 rounded-lg bg-[#F3F7F5] dark:bg-[#071E1F]">
                          {selectedJob.description}
                        </p>
                      </TabsContent>
                    </div>
                  </Tabs>
                </CardContent>
              </Card>
            ) : currentFeedJob ? (
              <Card>
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base">{currentFeedJob.title}</CardTitle>
                        <a
                          href={currentFeedJob.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#14746F] hover:text-[#0F3D3E] transition-colors"
                          title="Open on Upwork"
                        >
                          <ExternalLink className="size-4" />
                        </a>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <CardDescription className="font-mono text-[11px]">
                          Job ID: {currentFeedJob.uid} · Summary Preview
                        </CardDescription>

                        {(currentFeedJob.client_location || currentFeedJob.client_location_snippet || currentFeedJob.location) && (
                          <Badge variant="neutral" className="text-[10px] flex items-center gap-1 font-medium text-[#14746F] dark:text-[#8EB69B]">
                            <MapPin className="size-3" />
                            {currentFeedJob.client_location || currentFeedJob.client_location_snippet || currentFeedJob.location}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleExpandContracts}
                        disabled={expandMutation.isPending}
                      >
                        {expandMutation.isPending ? (
                          <RefreshCw className="size-3.5 me-1 animate-spin" />
                        ) : null}
                        Fetch Client History
                      </Button>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleRunPipeline}
                        disabled={pipelineMutation.isPending}
                      >
                        Auto-Find Leads
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-3.5 rounded-lg border border-[#636B2F]/30 bg-[#EFF4DC]/50 dark:bg-[#2B3118]/30 text-xs text-[#3D4127] dark:text-[#F8F9F3] space-y-1">
                    <div className="font-semibold text-[#636B2F] dark:text-[#D4DE95]">
                      Summary Preview Loaded
                    </div>
                    <p className="text-[11px] text-[#4D5333] dark:text-[#DCE1C4]">
                      Click &quot;Fetch Client History&quot; to retrieve client feedback, verify their business profile, and discover decision-makers on LinkedIn.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-[#EFF2E3] dark:bg-[#15180E] text-xs">
                    <div>
                      <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Budget Type</span>
                      <span className="font-semibold font-mono text-[#3D4127] dark:text-[#F8F9F3]">{cleanBudget(currentFeedJob.budget)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Experience Level</span>
                      <span className="font-semibold text-[#3D4127] dark:text-[#F8F9F3]">{cleanExperienceLevel(currentFeedJob.experience_level)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Client Spend</span>
                      <span className="font-semibold font-mono text-[#3D4127] dark:text-[#F8F9F3]">{currentFeedJob.client_spent || 'Hidden in feed'}</span>
                    </div>
                  </div>

                  {currentFeedJob.snippet && (
                    <div className="space-y-1">
                      <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] block">Feed Snippet:</span>
                      <p className="text-xs text-[#4D5333] dark:text-[#DCE1C4] leading-relaxed p-3 rounded-lg bg-[#EFF2E3] dark:bg-[#15180E]">
                        {currentFeedJob.snippet}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="p-12 text-center text-xs text-[#5A7E7B]">
                Select a job from the feed to view client details, contract history, and scored decision-makers.
              </Card>
            )}
          </div>
        </section>

        {/* Human-in-the-Loop Review Dialog Pattern */}
        <HitlReviewDialog
          open={isHitlDialogOpen}
          onOpenChange={setIsHitlDialogOpen}
          intelligence={intelligence || null}
          clientName={hitlClientName}
          onClientNameChange={setHitlClientName}
          companyName={hitlCompanyName}
          onCompanyNameChange={setHitlCompanyName}
          targetRole={hitlRole}
          onTargetRoleChange={setHitlRole}
          onConfirm={handleConfirmAndDiscover}
          isConfirming={confirmMutation.isPending || discoverMutation.isPending}
        />

        {/* Upwork Session Cookie Manager Dialog */}
        <SessionImportDialog
          open={isSessionDialogOpen}
          onOpenChange={setIsSessionDialogOpen}
          onImportSuccess={(_status: SessionStatusResponse) => {
            refetchSession();
          }}
        />

        {/* Harvested Jobs Explorer Modal */}
        <HarvestedJobsModal
          open={isHarvestedJobsModalOpen}
          onOpenChange={setIsHarvestedJobsModalOpen}
          onSelectJob={(uid) => {
            setSelectedJobUid(uid);
            setIsHarvestedJobsModalOpen(false);
          }}
        />

        {/* Job Domains & Query History Modal */}
        <JobDomainsModal
          open={isJobDomainsModalOpen}
          onOpenChange={setIsJobDomainsModalOpen}
          onLoadDomainJobs={handleLoadDomainJobs}
        />

        {/* Potential Clients Explorer Modal */}
        <PotentialClientsModal
          open={isPotentialClientsModalOpen}
          onOpenChange={setIsPotentialClientsModalOpen}
          onSelectJobUid={(uid) => {
            setSelectedJobUid(uid);
            setIsPotentialClientsModalOpen(false);
          }}
        />
      </main>
    </div>
  );
}
