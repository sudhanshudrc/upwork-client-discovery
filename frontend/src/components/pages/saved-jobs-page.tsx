import * as React from 'react';
import {
  Bookmark,
  Search,
  ExternalLink,
  MapPin,
  ChevronRight,
  DollarSign,
  ArrowLeft,
  Calendar,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useAllHarvestedJobs } from '@/hooks/use-dashboard';
import type { HarvestedJobItem } from '@/services/api';

interface SavedJobsPageProps {
  onSelectJob: (jobUid: string) => void;
  onBackToOverview: () => void;
}

export function SavedJobsPage({ onSelectJob, onBackToOverview }: SavedJobsPageProps) {
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={onBackToOverview}
            className="h-9 px-2.5 flex items-center gap-1 text-slate-600 dark:text-slate-300"
          >
            <ArrowLeft className="size-4" />
            <span>Overview</span>
          </Button>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-50 flex items-center gap-2">
              <Bookmark className="size-5 text-blue-600" />
              Saved Jobs Library
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Browse all {jobs?.length || 0} job postings collected across your previous searches
            </p>
          </div>
        </div>

        {/* Filter Input */}
        <div className="relative w-full sm:w-72">
          <Search className="size-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search by title, client, or location..."
            className="w-full h-9 pl-9 pr-3 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Jobs Table Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">
              Saved Postings ({filteredJobs.length})
            </CardTitle>
            <span className="text-xs text-slate-500">
              Click any job to open its full profile and contacts
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="py-16 text-center space-y-3">
              <Bookmark className="size-10 mx-auto text-slate-300 dark:text-slate-600" />
              <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                No saved jobs found
              </div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                {filterQuery
                  ? 'No results match your filter. Try clearing the search box.'
                  : 'Run your first search on the Search & Leads page to start saving jobs.'}
              </p>
              {!filterQuery && (
                <Button variant="primary" size="sm" onClick={onBackToOverview}>
                  Go to Job Search
                </Button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredJobs.map((job: HarvestedJobItem) => (
                <div
                  key={job.id}
                  onClick={() => onSelectJob(job.job_uid)}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors group"
                >
                  <div className="space-y-1.5 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-900 dark:text-slate-50 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
                        {job.title}
                      </span>
                      {job.job_url && (
                        <a
                          href={job.job_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                          title="Open on Upwork"
                        >
                          <ExternalLink className="size-3.5" />
                        </a>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                      {job.client_name && (
                        <Badge variant="brand" className="text-[11px] py-0">
                          Client: {job.client_name}
                        </Badge>
                      )}
                      {job.client_location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="size-3 text-slate-400" />
                          <span>{job.client_location}</span>
                        </span>
                      )}
                      {job.client_total_spent && (
                        <span className="flex items-center gap-1 font-mono">
                          <DollarSign className="size-3 text-emerald-600" />
                          <span>{job.client_total_spent} spent</span>
                        </span>
                      )}
                      {job.created_at && (
                        <span className="flex items-center gap-1 text-[11px]">
                          <Calendar className="size-3 text-slate-400" />
                          <span>{new Date(job.created_at).toLocaleDateString()}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="text-xs group-hover:border-blue-400"
                    >
                      <span>Inspect Job</span>
                      <ChevronRight className="size-3.5 ms-1" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
