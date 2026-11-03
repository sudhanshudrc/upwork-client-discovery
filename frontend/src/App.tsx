import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  ExternalLink,
  RefreshCw,
  UserCheck,
  AlertTriangle,
  Filter,
  MapPin,
  Sparkles,
  Loader2,
  Star,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';

// Navigation & Pages
import { AppHeader, type AppPage } from '@/components/patterns/app-header';
import { AuthPage } from '@/components/pages/auth-page';
import { SavedJobsPage } from '@/components/pages/saved-jobs-page';
import { SearchHistoryPage } from '@/components/pages/search-history-page';
import { ClientsPage } from '@/components/pages/clients-page';
import { ConnectionPage } from '@/components/pages/connection-page';

// Composed UI Patterns
import { StatGrid } from '@/components/patterns/stat-grid';
import { SearchHeader } from '@/components/patterns/search-header';
import { JobFeedTable } from '@/components/patterns/job-feed-table';
import { ContractHistoryCard } from '@/components/patterns/contract-history-card';
// import { CandidateRankingCard } from '@/components/patterns/candidate-ranking-card';
import { HitlReviewDialog } from '@/components/patterns/hitl-review-dialog';
import { PipelineProgressBar } from '@/components/patterns/pipeline-progress-bar';
import { IntelligenceCard } from '@/components/patterns/intelligence-card';
import { SearchDomainBar } from '@/components/patterns/search-domain-bar';

// Auth & Session
import { useAuth } from '@/context/auth-context';
import { useSessionStatus } from '@/hooks/use-session';
import { useJobSearch, useJobDetails, useExpandJob } from '@/hooks/use-jobs';
import { useIntelligence, useConfirmIntelligence } from '@/hooks/use-intelligence';
import { useDiscoverLeads } from '@/hooks/use-leads';
import { useRunSinglePipeline } from '@/hooks/use-pipeline';
import { useDashboardStats, useAllHarvestedJobs } from '@/hooks/use-dashboard';
import { useDomains } from '@/hooks/use-domains';
import {
  api,
  type FeedJobItem,
  type DecisionMakerDiscoveryResponse,
  getStoredUserIdentifier,
} from '@/services/api';

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
  const [currentPage, setCurrentPage] = React.useState<AppPage>('overview');

  // Search & Filter State
  const [searchQuery, setSearchQuery] = React.useState('Frontend Developer');
  const [limit, setLimit] = React.useState(3);
  const [forceLive, setForceLive] = React.useState(false);
  const [feedFilterText, setFeedFilterText] = React.useState('');
  const [jobs, setJobs] = React.useState<FeedJobItem[]>([]);
  const [selectedJobUid, setSelectedJobUid] = React.useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = React.useState<string | null>(null);

  // Auth State
  const { user, isAuthenticated, isLoading: isLoadingAuth } = useAuth();

  // Review Dialog State
  const [isHitlDialogOpen, setIsHitlDialogOpen] = React.useState(false);

  // Form State for Client Review
  const [hitlClientName, setHitlClientName] = React.useState('');
  const [hitlCompanyName, setHitlCompanyName] = React.useState('');
  const [hitlRole, setHitlRole] = React.useState('CTO');
  const [discoveryResult, setDiscoveryResult] = React.useState<DecisionMakerDiscoveryResponse | null>(null);
  const [activeTab, setActiveTab] = React.useState<string>('intelligence');
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [showPipelineProgress, setShowPipelineProgress] = React.useState(false);

  // User Profile
  const activeProfile = user ? user.email : getStoredUserIdentifier();

  // TanStack Query Hooks
  const queryClient = useQueryClient();
  const { data: sessionStatus, isLoading: isLoadingSession, refetch: refetchSession } = useSessionStatus(activeProfile);
  const searchMutation = useJobSearch();
  const expandMutation = useExpandJob();
  const confirmMutation = useConfirmIntelligence();
  const discoverMutation = useDiscoverLeads();
  const pipelineMutation = useRunSinglePipeline();

  const { data: dashboardStats } = useDashboardStats();
  const { data: allHarvestedJobs } = useAllHarvestedJobs();
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

  // Sync client verification fields when intelligence data loads
  React.useEffect(() => {
    if (intelligence) {
      const defaultName =
        intelligence.suggested_client_names?.[0] ||
        intelligence.suggested_client_name?.split(',')[0]?.trim() ||
        '';
      if (defaultName) setHitlClientName(defaultName);
      if (intelligence.suggested_company_name) setHitlCompanyName(intelligence.suggested_company_name);
      if (intelligence.suggested_role) setHitlRole(intelligence.suggested_role);
    }
  }, [intelligence]);

  // Synchronize detailed client rating back to feed jobs list
  React.useEffect(() => {
    if (selectedJob && selectedJob.job_uid && selectedJob.client) {
      setJobs((prevJobs) =>
        prevJobs.map((j) => {
          if (j.uid === selectedJob.job_uid) {
            const ratingStr = selectedJob.client?.client_rating ? String(selectedJob.client.client_rating) : j.client_rating;
            const spentStr = selectedJob.client?.total_spent_usd ? `$${Number(selectedJob.client.total_spent_usd).toLocaleString()} spent` : j.client_spent;
            const locStr = selectedJob.client?.country || j.location;
            const verified = selectedJob.client?.payment_verified ?? j.payment_verified;
            return {
              ...j,
              client_rating: ratingStr,
              client_spent: spentStr,
              location: locStr,
              payment_verified: verified,
            };
          }
          return j;
        })
      );
    }
  }, [selectedJob]);

  // Search Jobs Feed
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);

    searchMutation.mutate(
      { query: searchQuery, limit, forceLive },
      {
        onSuccess: (data) => {
          setJobs(data.jobs);
          if (data.db_run_id) {
            setCurrentRunId(data.db_run_id);
          }
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

  // Select Domain Keyword
  const handleSelectDomain = (domainQuery: string) => {
    setSearchQuery(domainQuery);
    setErrorMessage(null);
    searchMutation.mutate(
      { query: domainQuery, limit, forceLive: false },
      {
        onSuccess: (data) => {
          setJobs(data.jobs);
          if (data.db_run_id) {
            setCurrentRunId(data.db_run_id);
          }
          if (data.jobs.length > 0) {
            setSelectedJobUid(data.jobs[0].uid);
          }
        },
        onError: (err) => {
          setErrorMessage(err.message || 'Failed to load jobs for search keyword');
        },
      }
    );
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
          setErrorMessage(err.message || 'Failed to fetch contract history');
        },
      }
    );
  };

  // Open Client Review Dialog
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
    setActiveTab('intelligence');

    if (selectedJob?.id && hitlClientName.trim()) {
      confirmMutation.mutate(
        {
          job_id: selectedJob.id,
          job_uid: uid,
          confirmed_client_name: hitlClientName.trim(),
          confirmed_company_name: hitlCompanyName.trim(),
          target_role: hitlRole.trim() || 'CTO',
          is_agency: intelligence?.is_agency || false,
        },
        {
          onSuccess: () => {
            discoverMutation.mutate(uid, {
              onSuccess: (leads) => {
                setDiscoveryResult(leads);
                queryClient.invalidateQueries({ queryKey: ['job-details', uid] });
                queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
                queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
              },
              onError: (err) => {
                setErrorMessage(err.message || 'Failed to discover leads on LinkedIn');
              },
            });
          },
          onError: () => {
            discoverMutation.mutate(uid, {
              onSuccess: (leads) => {
                setDiscoveryResult(leads);
              },
            });
          },
        }
      );
      return;
    }

    discoverMutation.mutate(uid, {
      onSuccess: (leads) => {
        setDiscoveryResult(leads);
        queryClient.invalidateQueries({ queryKey: ['job-details', uid] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
      },
      onError: (err) => {
        setErrorMessage(err.message || 'Failed to discover leads on LinkedIn');
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
        confirmed_company_name: hitlCompanyName.trim(),
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
    setActiveTab('intelligence');

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
          setErrorMessage(err.message || 'Lead extraction failed');
        },
      }
    );
  };

  // Effective decision-maker discovery data (preserved for when LinkedIn UI is re-enabled)
  void discoveryResult;
  /*
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
  */

  // const candidatesCount =
  //   (effectiveDiscoveryData?.resolved_candidate ? 1 : 0) +
  //   (effectiveDiscoveryData?.potential_candidates?.length || 0);

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

  // Set of scraped job UIDs (from PostgreSQL harvested jobs + locally selected job)
  const scrapedJobUids = React.useMemo(() => {
    const set = new Set<string>();
    if (allHarvestedJobs) {
      allHarvestedJobs.forEach((hj) => set.add(hj.job_uid));
    }
    if (selectedJob?.job_uid) {
      set.add(selectedJob.job_uid);
    }
    return set;
  }, [allHarvestedJobs, selectedJob]);

  // Count how many of the currently loaded feed jobs have been scraped
  const scrapedCount = React.useMemo(() => {
    return jobs.filter((j) => scrapedJobUids.has(j.uid)).length;
  }, [jobs, scrapedJobUids]);

  const cookieMatch =
    sessionStatus?.message?.match(/with (\d+) cookies/i) ||
    sessionStatus?.message?.match(/\((\d+) cookies\)/i);
  const activeCookiesCount = cookieMatch
    ? Number(cookieMatch[1])
    : (user?.upwork_cookie_count || (sessionStatus?.is_authenticated ? 79 : 0));

  // Loading state while checking authentication
  if (isLoadingAuth) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-8 animate-spin text-blue-600" />
          <span className="text-xs text-slate-500">Loading your workspace...</span>
        </div>
      </div>
    );
  }

  // Not authenticated: Render dedicated Auth Page (Login / Sign Up)
  if (!isAuthenticated || !user) {
    return <AuthPage />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-200">
      {/* Top Header with Red Signal for Cookies */}
      <AppHeader
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        isDarkMode={isDarkMode}
        onToggleDarkMode={toggleDarkMode}
        sessionStatus={sessionStatus}
        isLoadingSession={isLoadingSession}
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Error Alert Display */}
        {errorMessage && (
          <div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-4 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
            <AlertTriangle className="size-4 shrink-0 text-red-600" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Dedicated Page Views (Replacing Modals) */}
        {currentPage === 'saved-jobs' && (
          <SavedJobsPage
            onSelectJob={(uid) => {
              setSelectedJobUid(uid);
              setCurrentPage('overview');
            }}
            onBackToOverview={() => setCurrentPage('overview')}
          />
        )}

        {currentPage === 'search-history' && (
          <SearchHistoryPage
            onRunSearch={(q) => {
              setSearchQuery(q);
              handleSearch();
              setCurrentPage('overview');
            }}
            onBackToOverview={() => setCurrentPage('overview')}
          />
        )}

        {currentPage === 'clients' && (
          <ClientsPage
            onSelectJob={(uid) => {
              setSelectedJobUid(uid);
              setCurrentPage('overview');
            }}
            onBackToOverview={() => setCurrentPage('overview')}
          />
        )}

        {currentPage === 'connection' && (
          <ConnectionPage
            currentProfile={activeProfile}
            sessionStatus={sessionStatus}
            onRefreshSession={() => {
              refetchSession();
              queryClient.invalidateQueries({ queryKey: ['session-status'] });
            }}
            onBackToOverview={() => setCurrentPage('overview')}
          />
        )}

        {/* Overview Cockpit View */}
        {currentPage === 'overview' && (
          <div className="space-y-6">
            {/* Global KPI Stat Grid - Clicking cards navigates to the full page */}
            <StatGrid
              harvestedJobsCount={dashboardStats?.harvested_jobs_count ?? jobs.length}
              uniqueDomainsCount={dashboardStats?.unique_domains_count ?? (domainList?.length || 0)}
              potentialClientsCount={dashboardStats?.potential_clients_count ?? 0}
              activeCookiesCount={activeCookiesCount}
              latestDomain={domainList?.[0]?.query || searchQuery}
              activeProfile={activeProfile}
              onNavigate={setCurrentPage}
            />

            {/* Pipeline Execution Progress */}
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
              exportBatchUrl={api.getBatchExcelExportUrl(searchQuery, currentRunId || undefined, false)}
            />

            {/* Search Keyword Domains Pill Bar */}
            <SearchDomainBar
              domains={domainList}
              activeQuery={searchQuery}
              onSelectDomain={handleSelectDomain}
              onOpenHistoryPage={() => setCurrentPage('search-history')}
            />

            {/* Two-Pane Cockpit */}
            <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Pane: Job Feed Listing (4 columns) */}
              <div className="lg:col-span-4 space-y-3">
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Found Jobs ({filteredJobs.length})
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                      Scraped: {scrapedCount} of {jobs.length}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Filter className="size-3 text-blue-600" />
                    <input
                      type="text"
                      value={feedFilterText}
                      onChange={(e) => setFeedFilterText(e.target.value)}
                      placeholder="Filter list..."
                      className="w-24 px-1.5 py-0.5 text-xs rounded border border-slate-300 dark:border-slate-700 bg-transparent outline-none focus:border-blue-500"
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
                            <CardTitle className="text-base text-slate-900 dark:text-slate-50">{selectedJob.title}</CardTitle>
                            <a
                              href={selectedJob.job_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-600 hover:text-blue-700 transition-colors"
                              title="Open on Upwork"
                            >
                              <ExternalLink className="size-4" />
                            </a>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 mt-1">
                            <CardDescription className="font-mono text-xs">
                              Job ID: {selectedJob.job_uid.slice(-8)}
                            </CardDescription>

                            {(selectedJob.client?.city || selectedJob.client?.country || currentFeedJob?.client_location || currentFeedJob?.client_location_snippet) && (
                              <Badge variant="neutral" className="text-xs flex items-center gap-1 font-medium">
                                <MapPin className="size-3 text-slate-400" />
                                {selectedJob.client?.city && selectedJob.client?.country
                                  ? `${selectedJob.client.city}, ${selectedJob.client.country}`
                                  : selectedJob.client?.country || currentFeedJob?.client_location || currentFeedJob?.client_location_snippet}
                              </Badge>
                            )}

                            {(hitlClientName || selectedJob.intelligence?.confirmed_client_name || intelligence?.suggested_client_name) && (
                              <Badge variant="brand" className="text-xs">
                                Client: {hitlClientName || selectedJob.intelligence?.confirmed_client_name || intelligence?.suggested_client_name}
                              </Badge>
                            )}

                            {(selectedJob.intelligence?.confirmed_company_name || intelligence?.suggested_company_name) && (
                              <Badge variant="neutral" className="text-xs">
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
                            Verify Client
                          </Button>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-5">
                      {/* Client Summary Metric Bar */}
                      {selectedJob.client && (
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                          <div>
                            <div className="text-[11px] text-slate-500">Total Spend</div>
                            <div className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-50">
                              ${Number(selectedJob.client.total_spent_usd || 0).toLocaleString()}
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] text-slate-500">Client Rating</div>
                            <div className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-50 flex items-center gap-1">
                              {selectedJob.client.client_rating && parseFloat(String(selectedJob.client.client_rating)) > 0 ? (
                                <>
                                  <Star className="size-3.5 text-amber-500 fill-amber-500" />
                                  <span>{String(selectedJob.client.client_rating)} / 5.0</span>
                                </>
                              ) : (
                                <span className="text-rose-600 dark:text-rose-400 text-xs font-medium">Unrated / New</span>
                              )}
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] text-slate-500">Hires / Active</div>
                            <div className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-50">
                              {selectedJob.client.total_hires || 0} / {selectedJob.client.active_hires || 0}
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] text-slate-500">Avg Hourly Rate</div>
                            <div className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-50">
                              ${selectedJob.client.avg_hourly_rate_usd || '0.00'} / hr
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] text-slate-500">Payment Status</div>
                            <div className="text-sm font-semibold text-emerald-600">
                              {selectedJob.client.payment_verified ? 'Verified' : 'Unverified'}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Multi-Tab Deep Inspector */}
                      <Tabs value={activeTab === 'candidates' ? 'intelligence' : activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid grid-cols-3 w-full">
                          <TabsTrigger value="intelligence" className="truncate">
                            Client Profile
                          </TabsTrigger>
                          <TabsTrigger value="contracts" className="truncate">
                            Past Contracts ({selectedJob.contracts?.length || 0})
                          </TabsTrigger>
                          {/* Tab 3: Decision-Makers Candidate Ranking Card (temporarily commented out in UI; backend endpoints preserved) */}
                          {/* <TabsTrigger value="candidates" className="truncate flex items-center justify-center gap-1.5">
                            <span>Decision-Makers</span>
                            {candidatesCount > 0 && (
                              <Badge variant="brand" className="px-1.5 py-0 text-[10px] leading-tight">
                                {candidatesCount}
                              </Badge>
                            )}
                          </TabsTrigger> */}
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
                              selectedClientName={hitlClientName}
                              onSelectClientName={(name) => setHitlClientName(name)}
                              selectedCompanyName={hitlCompanyName}
                              onSelectCompanyName={(comp) => setHitlCompanyName(comp)}
                              selectedRole={hitlRole}
                              onSelectRole={(role) => setHitlRole(role)}
                              onOpenReviewDialog={handleOpenHitl}
                              onDiscoverLeads={() => handleDirectDiscover(selectedJob.job_uid)}
                              isDiscovering={confirmMutation.isPending || discoverMutation.isPending}
                            />
                          </TabsContent>

                          {/* Tab 2: Contract History Card */}
                          <TabsContent value="contracts" className="pt-2 min-h-[440px]">
                            <ContractHistoryCard contracts={selectedJob.contracts} />
                          </TabsContent>

                          {/* Tab 3: Decision-Makers Candidate Ranking Card (temporarily commented out in UI; backend endpoints preserved) */}
                          {/* <TabsContent value="candidates" className="pt-2 min-h-[440px]">
                            <CandidateRankingCard
                              discoveryData={effectiveDiscoveryData}
                              jobUid={selectedJob.job_uid}
                              onMineIntelligence={() => handleDirectDiscover(selectedJob.job_uid)}
                              isLoading={discoverMutation.isPending}
                            />
                          </TabsContent> */}

                          {/* Tab 4: Job Description */}
                          <TabsContent value="description" className="pt-2 min-h-[440px]">
                            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
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
                              className="text-blue-600 hover:text-blue-700 transition-colors"
                              title="Open on Upwork"
                            >
                              <ExternalLink className="size-4" />
                            </a>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 mt-1">
                            <CardDescription className="font-mono text-xs">
                              Job ID: {currentFeedJob.uid} · Summary Preview
                            </CardDescription>

                            {(currentFeedJob.client_location || currentFeedJob.client_location_snippet || currentFeedJob.location) && (
                              <Badge variant="neutral" className="text-xs flex items-center gap-1 font-medium">
                                <MapPin className="size-3 text-slate-400" />
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
                            <Sparkles className="size-3.5 me-1" />
                            Auto-Find Leads
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="p-3.5 rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/30 text-xs text-slate-800 dark:text-slate-200 space-y-1">
                        <div className="font-semibold text-blue-700 dark:text-blue-300">
                          Summary Preview Loaded
                        </div>
                        <p className="text-[11px] text-slate-600 dark:text-slate-400">
                          Click &quot;Fetch Client History&quot; to retrieve client feedback and verify their business profile.
                        </p>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                        <div>
                          <span className="text-[10px] text-slate-500 block">Budget Type</span>
                          <span className="font-semibold font-mono text-slate-900 dark:text-slate-50">{cleanBudget(currentFeedJob.budget)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 block">Experience Level</span>
                          <span className="font-semibold text-slate-900 dark:text-slate-50">{cleanExperienceLevel(currentFeedJob.experience_level)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 block">Client Spend</span>
                          <span className="font-semibold font-mono text-slate-900 dark:text-slate-50">{currentFeedJob.client_spent || 'Hidden in feed'}</span>
                        </div>
                      </div>

                      {currentFeedJob.snippet && (
                        <div className="space-y-1">
                          <span className="text-xs font-semibold text-slate-500 block">Feed Snippet:</span>
                          <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                            {currentFeedJob.snippet}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="p-12 text-center text-xs text-slate-400">
                    Select a job from the feed to view client details and contract history.
                  </Card>
                )}
              </div>
            </section>
          </div>
        )}

        {/* Human Review Modal (Only opened when user explicitly clicks "Verify Client") */}
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
      </main>
    </div>
  );
}
