import { motion } from 'framer-motion';
import { ExternalLink, FileSpreadsheet, UserCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { staggerContainer, staggerItem } from '@/components/motion/library';
import { api, type DecisionMakerDiscoveryResponse } from '@/services/api';

interface CandidateRankingCardProps {
  discoveryData: DecisionMakerDiscoveryResponse | null;
  jobUid: string;
  onMineIntelligence?: () => void;
  isLoading?: boolean;
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
        label: `Public Web Search (#${index + 1})`,
        badge: 'Web Index',
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
          badge: 'Regional',
          badgeVariant: 'brand',
          description: `Direct LinkedIn search matching name and regional location`,
          url: rawUrl,
          queryParamText: decodedKeywords,
        };
      } else if (parts.length === 2 && index >= 2) {
        return {
          label: `Name + City Search (#${index + 1})`,
          badge: 'City Filter',
          badgeVariant: 'brand',
          description: `Direct LinkedIn search matching client name and city`,
          url: rawUrl,
          queryParamText: decodedKeywords,
        };
      }

      return {
        label: `Direct Name Search (#${index + 1})`,
        badge: 'Direct Name',
        badgeVariant: 'neutral',
        description: `Direct LinkedIn lookup for "${decodedKeywords || 'candidate'}"`,
        url: rawUrl,
        queryParamText: decodedKeywords,
      };
    }
  } catch {
    // Fallback if URL parsing encounters non-standard scheme
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

export function CandidateRankingCard({
  discoveryData,
  jobUid,
  onMineIntelligence,
  isLoading = false,
}: CandidateRankingCardProps) {
  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs text-[#636B2F] dark:text-[#D4DE95] border border-dashed border-[#BAC095] dark:border-[#2E331E] rounded-lg space-y-3 bg-[#EFF4DC]/20 dark:bg-[#2B3118]/20">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-[#636B2F] border-t-transparent" />
        <div className="font-semibold text-xs text-[#3D4127] dark:text-[#F8F9F3]">
          Searching LinkedIn & Scoring Decision-Makers...
        </div>
        <p className="text-[11px] text-[#656C43] dark:text-[#BAC095] max-w-sm mx-auto">
          Resolving location GeoURN, analyzing profile relevance, and calculating 4-factor match scores.
        </p>
      </div>
    );
  }

  const hasProfiles = Boolean(
    discoveryData &&
      (discoveryData.resolved_candidate ||
        (discoveryData.potential_candidates && discoveryData.potential_candidates.length > 0))
  );
  const hasSearches = Boolean(
    discoveryData &&
      discoveryData.direct_linkedin_search_urls &&
      discoveryData.direct_linkedin_search_urls.length > 0
  );

  if (!discoveryData || (!hasProfiles && !hasSearches)) {
    return (
      <div className="p-8 text-center text-xs text-[#656C43] dark:text-[#BAC095] border border-dashed border-[#BAC095] dark:border-[#2E331E] rounded-lg space-y-3">
        <div>No decision-makers identified yet for this job posting.</div>
        {onMineIntelligence && (
          <Button variant="secondary" size="sm" onClick={onMineIntelligence}>
            <UserCheck className="size-3.5 me-1" />
            Find Decision-Makers
          </Button>
        )}
      </div>
    );
  }

  const { resolved_candidate, potential_candidates = [], direct_linkedin_search_urls = [] } = discoveryData;

  return (
    <div className="space-y-4">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-1 border-b border-[#EFF2E3] dark:border-[#2E331E]">
        <div>
          <span className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
            Identified Decision-Makers
          </span>
          <span className="text-[11px] text-[#656C43] dark:text-[#BAC095] ms-2">
            Target Client: {discoveryData.client_name || 'Confirmed Client'}
          </span>
        </div>

        <a
          href={api.getExcelExportUrl(jobUid)}
          download
          className="inline-flex items-center text-xs font-semibold text-[#636B2F] dark:text-[#D4DE95] hover:underline"
        >
          <FileSpreadsheet className="size-3.5 me-1" />
          Export Leads (.xlsx)
        </a>
      </div>

      {/* Primary Resolved Candidate OR Notice */}
      {resolved_candidate ? (
        <Card className="border-[#636B2F] bg-[#EFF4DC]/40 dark:bg-[#2B3118]/40">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-bold text-[#3D4127] dark:text-[#F8F9F3]">
                  {resolved_candidate.full_name}
                </CardTitle>
                <Badge variant="tier-a">Best Match</Badge>
              </div>
              <span className="font-mono font-bold text-sm text-[#636B2F] dark:text-[#D4DE95]">
                {resolved_candidate.match_score}% Match
              </span>
            </div>
            <CardDescription className="text-xs text-[#4D5333] dark:text-[#DCE1C4]">
              {resolved_candidate.headline || 'Professional'} · {resolved_candidate.profile_location}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-xs text-[#4D5333] dark:text-[#DCE1C4]">
              {resolved_candidate.scoring_reasons?.join('; ')}
            </div>
            <a
              href={resolved_candidate.linkedin_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center text-xs text-[#636B2F] dark:text-[#D4DE95] font-semibold hover:underline pt-1"
            >
              Open LinkedIn Profile <ExternalLink className="size-3 ms-1" />
            </a>
          </CardContent>
        </Card>
      ) : potential_candidates.length > 0 ? (
        <div className="p-3.5 rounded-lg border border-[#BAC095] dark:border-[#2E331E] bg-[#EFF2E3] dark:bg-[#15180E] text-xs text-[#656C43] dark:text-[#BAC095]">
          No single Tier-A primary match resolved. Reviewing potential matches below.
        </div>
      ) : (
        <div className="p-3.5 rounded-lg border border-[#BAC095] dark:border-[#2E331E] bg-[#EFF4DC]/30 dark:bg-[#2B3118]/20 text-xs text-[#4D5333] dark:text-[#DCE1C4]">
          No public search profiles could be automatically matched yet. You can click any of the {direct_linkedin_search_urls.length} targeted search queries below to inspect decision-makers directly on LinkedIn.
        </div>
      )}

      {/* Ranked Potential Candidates */}
      {potential_candidates.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide">
            Possible Matches ({potential_candidates.length})
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="space-y-2.5"
          >
            {potential_candidates.map((cand, idx) => (
              <motion.div key={cand.id || idx} variants={staggerItem}>
                <Card className="p-3.5 hover:border-[#BAC095] transition-colors">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-[#3D4127] dark:text-[#F8F9F3]">
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
                        >
                          {cand.tier}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-[#656C43] dark:text-[#BAC095] mt-0.5">
                        {cand.headline} · {cand.profile_location}
                      </div>
                    </div>
                    <span className="font-mono font-semibold text-xs text-[#636B2F] dark:text-[#D4DE95]">
                      {cand.match_score}%
                    </span>
                  </div>

                  <div className="mt-2 pt-2 border-t border-[#EFF2E3] dark:border-[#2E331E] flex justify-between items-center text-[11px]">
                    <span className="text-[#656C43] dark:text-[#BAC095] text-[10px] line-clamp-1">
                      {cand.scoring_reasons?.[0]}
                    </span>
                    <a
                      href={cand.linkedin_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#636B2F] dark:text-[#D4DE95] hover:underline inline-flex items-center font-medium shrink-0 ms-2"
                    >
                      Profile <ExternalLink className="size-3 ms-0.5" />
                    </a>
                  </div>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      )}

      {/* Direct LinkedIn Search Actions */}
      {direct_linkedin_search_urls && direct_linkedin_search_urls.length > 0 && (
        <div className="space-y-2.5 pt-3 border-t border-[#E1E4D3] dark:border-[#2E331E]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
              Direct LinkedIn Searches ({direct_linkedin_search_urls.length})
            </span>
            <span className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Click any search to verify profiles directly
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {direct_linkedin_search_urls.map((rawUrl, idx) => {
              const info = parseSearchQuery(rawUrl, idx);
              return (
                <a
                  key={idx}
                  href={info.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group relative flex flex-col justify-between p-3 rounded-lg border border-[#BAC095] dark:border-[#2E331E] bg-white dark:bg-[#15180E] hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-[#3D4127] dark:text-[#F8F9F3] group-hover:text-[#636B2F] dark:group-hover:text-[#D4DE95] transition-colors">
                      <ExternalLink className="size-3.5 text-[#636B2F] dark:text-[#D4DE95] shrink-0" />
                      <span>{info.label}</span>
                    </div>
                    <Badge variant={info.badgeVariant} className="text-[10px] shrink-0">
                      {info.badge}
                    </Badge>
                  </div>

                  <p className="text-[11px] text-[#656C43] dark:text-[#BAC095] mt-1.5 line-clamp-1">
                    {info.description}
                  </p>

                  <div className="mt-2 pt-2 border-t border-[#EFF2E3] dark:border-[#2E331E] flex items-center justify-between text-[10px]">
                    <span className="font-mono text-[#4D5333] dark:text-[#DCE1C4] truncate max-w-[190px]">
                      {info.queryParamText}
                    </span>
                    <span className="text-[#636B2F] dark:text-[#D4DE95] font-semibold group-hover:underline inline-flex items-center gap-0.5 shrink-0">
                      Open Search &rarr;
                    </span>
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
