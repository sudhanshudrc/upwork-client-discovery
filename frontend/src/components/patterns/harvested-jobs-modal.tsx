import * as React from 'react';
import { ExternalLink, Search, MapPin, Briefcase, ChevronRight, CheckCircle2 } from 'lucide-react';
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
import { useAllHarvestedJobs } from '@/hooks/use-dashboard';
import type { HarvestedJobItem } from '@/services/api';

interface HarvestedJobsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectJob: (jobUid: string) => void;
}

export function HarvestedJobsModal({
  open,
  onOpenChange,
  onSelectJob,
}: HarvestedJobsModalProps) {
  const { data: jobs, isLoading } = useAllHarvestedJobs();
  const [filterQuery, setFilterQuery] = React.useState('');

  const filteredJobs = React.useMemo(() => {
    if (!jobs) return [];
    if (!filterQuery.trim()) return jobs;
    const q = filterQuery.toLowerCase();
    return jobs.filter(
      (j) =>
        j.title.toLowerCase().includes(q) ||
        j.job_uid.toLowerCase().includes(q) ||
        (j.client_location && j.client_location.toLowerCase().includes(q)) ||
        (j.client_name && j.client_name.toLowerCase().includes(q))
    );
  }, [jobs, filterQuery]);

  const handleInspect = (jobUid: string) => {
    onSelectJob(jobUid);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col p-6">
        <DialogHeader className="pb-3 border-b border-[#E1EBE6] dark:border-[#2C5756]">
          <div className="flex items-center justify-between pe-6">
            <div>
              <DialogTitle className="text-base flex items-center gap-2">
                <Briefcase className="size-4 text-[#14746F]" />
                All Harvested Jobs Explorer
              </DialogTitle>
              <DialogDescription className="text-xs">
                Comprehensive database view of all job postings captured across search queries.
              </DialogDescription>
            </div>
            <Badge variant="brand" className="text-xs font-mono">
              {jobs?.length || 0} Total in Database
            </Badge>
          </div>

          <div className="pt-3">
            <div className="relative">
              <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#656C43] dark:text-[#BAC095]" />
              <input
                type="text"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                placeholder="Filter by title, ID, client location, or client name..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] outline-none focus:border-[#636B2F]"
              />
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-2 space-y-2">
          {isLoading ? (
            <div className="space-y-2 py-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="p-3 border rounded-lg space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              ))}
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#656C43] dark:text-[#BAC095] border border-dashed border-[#BAC095] rounded-lg space-y-1">
              <div>No harvested jobs found matching your filter criteria.</div>
              <div className="text-[11px] text-[#656C43]/80 dark:text-[#BAC095]/80">
                Execute a search query from the main dashboard to save jobs.
              </div>
            </div>
          ) : (
            <div className="divide-y divide-[#E1E4D3] dark:divide-[#2E331E]">
              {filteredJobs.map((job: HarvestedJobItem) => (
                <div
                  key={job.id}
                  className="py-3 px-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[#EFF2E3]/60 dark:hover:bg-[#2B3118]/30 rounded-lg transition-colors"
                >
                  <div className="space-y-1 max-w-xl">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-[#3D4127] dark:text-[#F8F9F3] line-clamp-1">
                        {job.title}
                      </span>
                      <Badge
                        variant={job.is_expanded ? 'tier-a' : 'neutral'}
                        className="text-[10px] py-0 px-1.5 shrink-0"
                      >
                        {job.is_expanded ? (
                          <span className="flex items-center gap-0.5">
                            <CheckCircle2 className="size-2.5" /> History Loaded
                          </span>
                        ) : (
                          'Saved'
                        )}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#656C43] dark:text-[#BAC095]">
                      <span className="font-mono">ID: {job.job_uid.slice(-8)}</span>

                      {job.client_location && (
                        <span className="flex items-center gap-0.5">
                          <MapPin className="size-3 text-[#636B2F] dark:text-[#D4DE95]" />
                          {job.client_location}
                        </span>
                      )}

                      {job.client_name && (
                        <span className="font-medium text-[#636B2F] dark:text-[#D4DE95]">
                          Client: {job.client_name}
                        </span>
                      )}

                      {job.pay_type && (
                        <span className="font-medium">
                          {job.pay_type}
                          {job.budget_max_usd ? ` ($${job.budget_max_usd})` : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded text-[#656C43] dark:text-[#BAC095] hover:text-[#636B2F] dark:hover:text-[#D4DE95] hover:bg-white dark:hover:bg-[#202414] transition-colors"
                      title="Open on Upwork"
                    >
                      <ExternalLink className="size-3.5" />
                    </a>

                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleInspect(job.job_uid)}
                      className="text-xs h-7 px-2.5"
                    >
                      Inspect in Cockpit <ChevronRight className="size-3 ms-1" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

