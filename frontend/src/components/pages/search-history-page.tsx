import * as React from 'react';
import {
  History,
  Search,
  ArrowLeft,
  Play,
  Clock,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDomains } from '@/hooks/use-domains';

interface SearchHistoryPageProps {
  onRunSearch: (query: string) => void;
  onBackToOverview: () => void;
}

export function SearchHistoryPage({
  onRunSearch,
  onBackToOverview,
}: SearchHistoryPageProps) {
  const { data: domains, isLoading } = useDomains();
  const [filterQuery, setFilterQuery] = React.useState('');

  const filteredDomains = React.useMemo(() => {
    if (!domains) return [];
    if (!filterQuery.trim()) return domains;
    const q = filterQuery.toLowerCase();
    return domains.filter((d) => d.query.toLowerCase().includes(q));
  }, [domains, filterQuery]);

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
              <History className="size-5 text-blue-600" />
              Search History
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Quickly re-run previous job searches or view saved results
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
            placeholder="Filter previous keywords..."
            className="w-full h-9 pl-9 pr-3 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Grid of Search Queries */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-xl" />
          ))}
        </div>
      ) : filteredDomains.length === 0 ? (
        <Card className="p-16 text-center space-y-3">
          <History className="size-10 mx-auto text-slate-300 dark:text-slate-600" />
          <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
            No search history found
          </div>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Searches you perform will be saved here so you can easily run them again with fresh results.
          </p>
          <Button variant="primary" size="sm" onClick={onBackToOverview}>
            Start a Search
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDomains.map((domain) => (
            <Card
              key={domain.query}
              className="hover:border-blue-400 hover:shadow-md transition-all group p-5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                      Search Keyword
                    </span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-50 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {domain.query}
                    </h3>
                  </div>
                  <Badge variant="brand" className="text-xs">
                    {domain.total_jobs_found} jobs
                  </Badge>
                </div>

                <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                  <Clock className="size-3.5 text-slate-400" />
                  <span>
                    Last searched: {domain.latest_run_at ? new Date(domain.latest_run_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    onRunSearch(domain.query);
                    onBackToOverview();
                  }}
                  className="text-xs flex items-center justify-center gap-1 w-full"
                >
                  <Play className="size-3" />
                  <span>Run Search Again</span>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
