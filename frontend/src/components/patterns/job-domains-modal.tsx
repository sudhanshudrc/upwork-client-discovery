import * as React from 'react';
import { Compass, Clock, CheckCircle2, AlertCircle, Layers, ArrowRight } from 'lucide-react';
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
import { useDomains } from '@/hooks/use-domains';
import { api, type FeedJobItem, type JobDomainItem } from '@/services/api';

interface JobDomainsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLoadDomainJobs: (query: string, jobs: FeedJobItem[]) => void;
}

export function JobDomainsModal({
  open,
  onOpenChange,
  onLoadDomainJobs,
}: JobDomainsModalProps) {
  const { data: domains, isLoading } = useDomains();
  const [loadingQuery, setLoadingQuery] = React.useState<string | null>(null);

  const handleLoadJobs = async (domain: JobDomainItem) => {
    try {
      setLoadingQuery(domain.query);
      const res = await api.getDomainJobs(domain.query);
      onLoadDomainJobs(domain.query, res.jobs);
      onOpenChange(false);
    } catch {
      // ignore
    } finally {
      setLoadingQuery(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-6">
        <DialogHeader className="pb-3 border-b border-[#E1EBE6] dark:border-[#2C5756]">
          <div className="flex items-center justify-between pe-6">
            <div>
              <DialogTitle className="text-base flex items-center gap-2">
                <Compass className="size-4 text-[#14746F]" />
                Job Domains & Search History Directory
              </DialogTitle>
              <DialogDescription className="text-xs">
                Query keywords executed throughout the platform with real-time 1-hour database cache state.
              </DialogDescription>
            </div>
            <Badge variant="brand" className="text-xs font-mono">
              {domains?.length || 0} Domains
            </Badge>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-2 space-y-2.5">
          {isLoading ? (
            <div className="space-y-2 py-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="p-4 border rounded-lg space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              ))}
            </div>
          ) : !domains || domains.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#656C43] dark:text-[#BAC095] border border-dashed border-[#BAC095] rounded-lg space-y-1">
              <div>No search query domains registered yet.</div>
              <div className="text-[11px] text-[#656C43]/80 dark:text-[#BAC095]/80">
                Search for jobs to save keyword domains and view cached results.
              </div>
            </div>
          ) : (
            domains.map((domain: JobDomainItem) => {
              const runDate = new Date(domain.latest_run_at);
              const formattedDate = runDate.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <div
                  key={domain.query}
                  className="p-4 rounded-lg border border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#15180E] hover:border-[#636B2F] dark:hover:border-[#D4DE95] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#3D4127] dark:text-[#F8F9F3]">
                        &quot;{domain.query}&quot;
                      </span>

                      {domain.is_cache_active ? (
                        <Badge variant="tier-a" className="text-[10px] py-0 px-2 flex items-center gap-1">
                          <CheckCircle2 className="size-2.5 text-[#636B2F] dark:text-[#D4DE95]" />
                          Cached ({domain.expires_in_minutes}m remaining)
                        </Badge>
                      ) : (
                        <Badge variant="neutral" className="text-[10px] py-0 px-2 flex items-center gap-1">
                          <AlertCircle className="size-2.5 text-[#656C43] dark:text-[#BAC095]" />
                          Live Refresh Ready
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-[#656C43] dark:text-[#BAC095]">
                      <span className="flex items-center gap-1 font-mono">
                        <Layers className="size-3" />
                        {domain.total_jobs_found} jobs found
                      </span>

                      <span>·</span>

                      <span>
                        {domain.total_runs_count} {domain.total_runs_count === 1 ? 'search' : 'searches'}
                      </span>

                      <span>·</span>

                      <span className="flex items-center gap-1">
                        <Clock className="size-3" />
                        {formattedDate}
                      </span>
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="primary"
                    disabled={loadingQuery === domain.query}
                    onClick={() => handleLoadJobs(domain)}
                    className="text-xs h-8 px-3 shrink-0 self-end sm:self-center"
                  >
                    {loadingQuery === domain.query ? (
                      'Loading...'
                    ) : (
                      <>
                        Load Extracted Jobs <ArrowRight className="size-3 ms-1" />
                      </>
                    )}
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
