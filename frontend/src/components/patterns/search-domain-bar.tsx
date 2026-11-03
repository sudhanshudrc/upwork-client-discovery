import { History, ChevronRight } from 'lucide-react';
import type { JobDomainItem } from '@/services/api';

interface SearchDomainBarProps {
  domains?: JobDomainItem[];
  activeQuery?: string;
  onSelectDomain: (query: string) => void;
  onOpenHistoryPage?: () => void;
}

export function SearchDomainBar({
  domains = [],
  activeQuery,
  onSelectDomain,
  onOpenHistoryPage,
}: SearchDomainBarProps) {
  if (!domains || domains.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto py-1 text-xs no-scrollbar">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 shrink-0 pe-1">
        <History className="size-3.5 text-blue-600" />
        <span>Recent Searches:</span>
      </div>

      <div className="flex items-center gap-2 flex-nowrap">
        {domains.slice(0, 6).map((domain) => {
          const isActive = activeQuery?.trim().toLowerCase() === domain.query.trim().toLowerCase();
          return (
            <button
              key={domain.query}
              type="button"
              onClick={() => onSelectDomain(domain.query)}
              className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium transition-all shrink-0 ${
                isActive
                  ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-blue-400'
              }`}
            >
              <span className="font-semibold">{domain.query}</span>

              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                {domain.total_jobs_found}
              </span>

              {domain.is_cache_active && (
                <span
                  title={`Cached in database for ${domain.expires_in_minutes} more minutes`}
                  className={`size-2 rounded-full ${
                    isActive ? 'bg-blue-200' : 'bg-blue-600'
                  }`}
                />
              )}
            </button>
          );
        })}

        {onOpenHistoryPage && (
          <button
            type="button"
            onClick={onOpenHistoryPage}
            className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-0.5 shrink-0 px-2"
          >
            <span>All History</span>
            <ChevronRight className="size-3" />
          </button>
        )}
      </div>
    </div>
  );
}
