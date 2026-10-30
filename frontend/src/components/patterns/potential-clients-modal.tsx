import * as React from 'react';
import {
  Users,
  MapPin,
  ExternalLink,
  Star,
  Briefcase,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardClients } from '@/hooks/use-dashboard';
import type { DashboardClientItem, DiscoveredCandidateSummary } from '@/services/api';

interface PotentialClientsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectJobUid?: (uid: string) => void;
}

interface SearchQueryMeta {
  label: string;
  badge: string;
  badgeVariant: 'tier-a' | 'tier-b' | 'tier-c' | 'brand' | 'neutral';
  description: string;
  url: string;
  queryParamText: string;
}

function parseSearchQuery(rawUrl: string, index: number): SearchQueryMeta {
  try {
    const parsed = new URL(rawUrl);
    const isGoogle = parsed.hostname.includes('google');
    const isLinkedIn = parsed.hostname.includes('linkedin');

    if (isGoogle) {
      const q = parsed.searchParams.get('q') || '';
      return {
        label: `Web Index Search (#${index + 1})`,
        badge: 'Web Search',
        badgeVariant: 'brand',
        description: 'Searches public web records for matching profiles',
        url: rawUrl,
        queryParamText: q,
      };
    }

    if (isLinkedIn) {
      const keywords = parsed.searchParams.get('keywords') || '';
      const geoUrn = parsed.searchParams.get('geoUrn');
      const firstName = parsed.searchParams.get('firstName') || '';
      const lastName = parsed.searchParams.get('lastName') || '';

      if (geoUrn) {
        return {
          label: `Target Metro Search (#${index + 1})`,
          badge: 'Metro Filter',
          badgeVariant: 'tier-a',
          description: `Direct LinkedIn search filtered by client's verified metro area`,
          url: rawUrl,
          queryParamText: keywords || `${firstName} ${lastName}`.trim(),
        };
      }

      const decodedKeywords = decodeURIComponent(keywords).trim();
      const parts = decodedKeywords.split(/\s+/);

      if (parts.length >= 3) {
        return {
          label: `Name + Region Search (#${index + 1})`,
          badge: 'Name + Region',
          badgeVariant: 'brand',
          description: `Direct people search matching full name and country/region keyword`,
          url: rawUrl,
          queryParamText: decodedKeywords,
        };
      } else if (parts.length === 2 && index >= 2) {
        return {
          label: `Name + City Search (#${index + 1})`,
          badge: 'City Facet',
          badgeVariant: 'brand',
          description: `Direct people search matching confirmed name and city keyword`,
          url: rawUrl,
          queryParamText: decodedKeywords,
        };
      }

      return {
        label: `Worldwide Name Search (#${index + 1})`,
        badge: 'Worldwide',
        badgeVariant: 'neutral',
        description: `Direct unfiltered global people lookup for "${decodedKeywords || 'candidate'}"`,
        url: rawUrl,
        queryParamText: decodedKeywords,
      };
    }
  } catch {
    // fallback
  }

  return {
    label: `Search Query #${index + 1}`,
    badge: 'Query',
    badgeVariant: 'neutral',
    description: 'External candidate search query',
    url: rawUrl,
    queryParamText: rawUrl,
  };
}

export function PotentialClientsModal({
  open,
  onOpenChange,
  onSelectJobUid,
}: PotentialClientsModalProps) {
  const { data: clients, isLoading } = useDashboardClients();
  const [selectedClientId, setSelectedClientId] = React.useState<string | null>(null);

  // Auto-select first client once loaded
  React.useEffect(() => {
    if (clients && clients.length > 0 && !selectedClientId) {
      setSelectedClientId(clients[0].client_id);
    }
  }, [clients, selectedClientId]);

  const activeClient = React.useMemo(() => {
    if (!clients) return null;
    return clients.find((c) => c.client_id === selectedClientId) || clients[0] || null;
  }, [clients, selectedClientId]);

  const handleInspectJob = (uid: string) => {
    onSelectJobUid?.(uid);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col p-6">
        <DialogHeader className="pb-3 border-b border-[#E1EBE6] dark:border-[#2C5756]">
          <div className="flex items-center justify-between pe-6">
            <div>
              <DialogTitle className="text-base flex items-center gap-2">
                <Users className="size-4 text-[#14746F]" />
                Potential Clients & Decision-Maker Directory
              </DialogTitle>
              <DialogDescription className="text-xs">
                All clients fetched till now with mined identities, origin job postings, spend, and verified LinkedIn candidates.
              </DialogDescription>
            </div>
            <Badge variant="brand" className="text-xs font-mono">
              {clients?.length || 0} Clients Identified
            </Badge>
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 grid grid-cols-1 md:grid-cols-12 gap-6">
            <div className="md:col-span-4 space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="p-3 border rounded-lg space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))}
            </div>
            <div className="md:col-span-8 p-4 border rounded-lg space-y-3">
              <Skeleton className="h-6 w-1/2" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          </div>
        ) : !clients || clients.length === 0 ? (
          <div className="p-16 text-center text-xs text-[#5A7E7B] border border-dashed rounded-lg space-y-2 my-4">
            <div className="font-semibold text-sm text-[#0A292A] dark:text-[#FBFCFC]">
              No clients with identified details yet.
            </div>
            <p className="max-w-md mx-auto text-[11px] text-[#365B58] dark:text-[#97C4AB]">
              Select a job posting and click &quot;Verify Client Details&quot; to discover decision-makers and populate this directory.
            </p>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-5 overflow-hidden py-3">
            {/* Left Column: Client List Master (4 columns) */}
            <div className="md:col-span-5 overflow-y-auto space-y-2 pe-1 border-e border-[#E1E4D3] dark:border-[#2E331E]">
              {clients.map((client: DashboardClientItem) => {
                const isSelected = activeClient?.client_id === client.client_id;
                return (
                  <div
                    key={client.client_id}
                    onClick={() => setSelectedClientId(client.client_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all text-left ${
                      isSelected
                        ? 'border-[#636B2F] bg-[#EFF4DC]/60 dark:bg-[#2B3118]/40 shadow-sm'
                        : 'border-[#BAC095] dark:border-[#2E331E] bg-white dark:bg-[#15180E] hover:border-[#636B2F]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-bold text-xs text-[#3D4127] dark:text-[#F8F9F3]">
                          {client.client_name}
                          {client.company_name ? ` · ${client.company_name}` : ''}
                        </div>
                        <div className="text-[10px] text-[#656C43] dark:text-[#BAC095] flex items-center gap-1 mt-0.5">
                          <MapPin className="size-2.5 text-[#636B2F] dark:text-[#D4DE95]" />
                          {client.location}
                        </div>
                      </div>

                      {client.tier_a_candidate ? (
                        <Badge variant="tier-a" className="text-[10px] py-0 px-1.5 shrink-0">
                          Tier A Match
                        </Badge>
                      ) : client.discovered_candidates_count > 0 ? (
                        <Badge variant="brand" className="text-[10px] py-0 px-1.5 shrink-0">
                          {client.discovered_candidates_count} Leads
                        </Badge>
                      ) : null}
                    </div>

                    <div className="mt-2 pt-2 border-t border-[#EFF2E3] dark:border-[#2E331E] flex items-center justify-between text-[10px] text-[#656C43] dark:text-[#BAC095]">
                      <span className="font-mono">
                        ${Number(client.total_spent_usd).toLocaleString()} spent
                      </span>
                      <span className="truncate max-w-[140px] text-[#4D5333] dark:text-[#DCE1C4]">
                        {client.origin_job.title}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Right Column: Detailed Client & Discovered Candidates Profile (7 columns) */}
            <div className="md:col-span-7 overflow-y-auto space-y-4 ps-1">
              {activeClient && (
                <div className="space-y-4">
                  {/* Client Summary Banner */}
                  <div className="p-4 rounded-lg bg-[#EFF2E3] dark:bg-[#15180E] border border-[#BAC095] dark:border-[#2E331E] space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h4 className="font-bold text-sm text-[#3D4127] dark:text-[#F8F9F3] flex items-center gap-2">
                          {activeClient.client_name}
                          {activeClient.company_name && (
                            <Badge variant="neutral" className="text-[10px] font-normal">
                              {activeClient.company_name}
                            </Badge>
                          )}
                          <Badge variant="brand" className="text-[10px]">
                            {activeClient.target_role || 'CTO'}
                          </Badge>
                        </h4>
                        <div className="text-xs text-[#656C43] dark:text-[#BAC095] flex items-center gap-1 mt-0.5">
                          <MapPin className="size-3 text-[#636B2F] dark:text-[#D4DE95]" />
                          {activeClient.location}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleInspectJob(activeClient.origin_job.job_uid)}
                          className="text-xs h-7 px-2.5"
                        >
                          <Briefcase className="size-3 me-1" />
                          View Origin Job
                        </Button>
                      </div>
                    </div>

                    {/* Spend, Hires & Rating Bar */}
                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#E1E4D3] dark:border-[#2E331E] text-xs">
                      <div>
                        <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Total Upwork Spend</span>
                        <span className="font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
                          ${Number(activeClient.total_spent_usd).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Past Hires</span>
                        <span className="font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
                          {activeClient.total_hires} ({activeClient.active_hires} active)
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] block">Client Rating</span>
                        <span className="font-bold font-mono text-[#636B2F] dark:text-[#D4DE95] flex items-center gap-0.5">
                          <Star className="size-3 fill-current" />
                          {activeClient.client_rating} / 5.0
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Origin Job Posting Link */}
                  <div className="p-3 rounded-lg border border-[#BAC095] dark:border-[#2E331E] bg-white dark:bg-[#15180E] text-xs space-y-1">
                    <span className="text-[10px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide block">
                      Originating Upwork Job Posting:
                    </span>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-[#3D4127] dark:text-[#F8F9F3] line-clamp-1">
                        {activeClient.origin_job.title}
                      </span>
                      <a
                        href={activeClient.origin_job.job_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#636B2F] dark:text-[#D4DE95] hover:underline inline-flex items-center text-[11px] font-semibold shrink-0"
                      >
                        Open on Upwork <ExternalLink className="size-3 ms-1" />
                      </a>
                    </div>
                  </div>

                  {/* Discovered Candidates Section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#0F3D3E] dark:text-[#FBFCFC]">
                        Discovered Decision-Maker Candidates ({activeClient.candidates.length})
                      </span>
                    </div>

                    {activeClient.candidates.length === 0 ? (
                      <div className="p-4 rounded-lg border border-dashed text-center text-xs text-[#5A7E7B]">
                        No candidate profiles matched yet for this client.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {activeClient.candidates.map((cand: DiscoveredCandidateSummary) => (
                          <div
                            key={cand.id}
                            className={`p-3 rounded-lg border transition-all text-xs ${
                              cand.tier.includes('Tier A')
                                ? 'border-[#636B2F] bg-[#EFF4DC]/40 dark:bg-[#2B3118]/30'
                                : 'border-[#BAC095] dark:border-[#2E331E] bg-white dark:bg-[#15180E]'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-[#3D4127] dark:text-[#F8F9F3]">
                                    #{cand.rank_order} {cand.full_name}
                                  </span>
                                  <Badge
                                    variant={
                                      cand.tier.includes('Tier A')
                                        ? 'tier-a'
                                        : cand.tier.includes('Tier B')
                                        ? 'tier-b'
                                        : 'tier-c'
                                    }
                                    className="text-[10px]"
                                  >
                                    {cand.tier}
                                  </Badge>
                                </div>
                                <p className="text-[11px] text-[#656C43] dark:text-[#BAC095] mt-0.5 line-clamp-1">
                                  {cand.headline || 'Professional'} · {cand.profile_location}
                                </p>
                              </div>

                              <span className="font-mono font-bold text-xs text-[#636B2F] dark:text-[#D4DE95]">
                                {cand.match_score}%
                              </span>
                            </div>

                            <div className="mt-2 pt-2 border-t border-[#EFF2E3] dark:border-[#2E331E] flex items-center justify-between text-[11px]">
                              <span className="text-[10px] text-[#656C43] dark:text-[#BAC095] truncate max-w-[200px]">
                                {cand.scoring_reasons?.[0] || 'Profile scored via 4-factor weights'}
                              </span>

                              <a
                                href={cand.linkedin_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[#636B2F] dark:text-[#D4DE95] font-semibold hover:underline inline-flex items-center gap-1 shrink-0"
                              >
                                View LinkedIn Profile <ExternalLink className="size-3" />
                              </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Direct LinkedIn Search Queries */}
                  {activeClient.direct_search_urls.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-[#E1E4D3] dark:border-[#2E331E]">
                      <span className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
                        Direct LinkedIn Searches ({activeClient.direct_search_urls.length})
                      </span>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {activeClient.direct_search_urls.map((rawUrl, idx) => {
                          const info = parseSearchQuery(rawUrl, idx);
                          return (
                            <a
                              key={idx}
                              href={info.url}
                              target="_blank"
                              rel="noreferrer"
                              className="group p-2.5 rounded-lg border border-[#BAC095] dark:border-[#2E331E] bg-white dark:bg-[#15180E] hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all text-left flex flex-col justify-between"
                            >
                              <div className="flex items-center justify-between gap-1">
                                <span className="font-semibold text-[11px] text-[#3D4127] dark:text-[#F8F9F3] group-hover:text-[#636B2F] dark:group-hover:text-[#D4DE95] flex items-center gap-1">
                                  <ExternalLink className="size-3 text-[#636B2F] dark:text-[#D4DE95]" />
                                  {info.label}
                                </span>
                                <Badge variant={info.badgeVariant} className="text-[9px] py-0 px-1">
                                  {info.badge}
                                </Badge>
                              </div>
                              <p className="text-[10px] text-[#656C43] dark:text-[#BAC095] mt-1 line-clamp-1">
                                {info.description}
                              </p>
                              <div className="mt-1.5 pt-1.5 border-t border-[#EFF2E3] dark:border-[#2E331E] flex items-center justify-between text-[9px]">
                                <span className="font-mono text-[#4D5333] dark:text-[#DCE1C4] truncate max-w-[130px]">
                                  {info.queryParamText}
                                </span>
                                <span className="text-[#636B2F] dark:text-[#D4DE95] font-semibold group-hover:underline">
                                  Search &rarr;
                                </span>
                              </div>
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
