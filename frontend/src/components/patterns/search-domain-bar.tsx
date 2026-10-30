import { Compass, ChevronRight } from 'lucide-react';
import type { JobDomainItem } from '@/services/api';

interface SearchDomainBarProps {
  domains?: JobDomainItem[];
  activeQuery?: string;
  onSelectDomain: (query: string) => void;
  onOpenDomainsModal?: () => void;
}

export function SearchDomainBar({
  domains = [],
  activeQuery,
  onSelectDomain,
  onOpenDomainsModal,
}: SearchDomainBarProps) {
  if (!domains || domains.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto py-1 text-xs no-scrollbar">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] shrink-0 pe-1">
        <Compass className="size-3.5 text-[#636B2F] dark:text-[#D4DE95]" />
        <span>Saved Searches:</span>
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
                  ? 'border-[#636B2F] bg-[#636B2F] text-[#F8F9F3] shadow-sm'
                  : 'border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] text-[#3D4127] dark:text-[#F8F9F3] hover:border-[#636B2F]'
              }`}
            >
              <span className="font-semibold">{domain.query}</span>

              <span
                className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'bg-[#EFF2E3] dark:bg-[#15180E] text-[#656C43] dark:text-[#BAC095]'
                }`}
              >
                {domain.total_jobs_found}
              </span>

              {domain.is_cache_active ? (
                <span
                  title={`Cached in database for ${domain.expires_in_minutes} more minutes`}
                  className={`size-2 rounded-full ${
                    isActive ? 'bg-[#D4DE95]' : 'bg-[#636B2F]'
                  }`}
                />
              ) : (
                <span
                  title="Cache expired (> 1 hour ago)"
                  className="size-2 rounded-full bg-[#B91C1C]/50"
                />
              )}
            </button>
          );
        })}

        {domains.length > 6 && onOpenDomainsModal && (
          <button
            type="button"
            onClick={onOpenDomainsModal}
            className="text-[11px] text-[#636B2F] dark:text-[#D4DE95] hover:underline font-semibold flex items-center gap-0.5 shrink-0 px-2 py-1"
          >
            +{domains.length - 6} more <ChevronRight className="size-3" />
          </button>
        )}
      </div>
    </div>
  );
}
