import * as React from 'react';
import { Search, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface SearchHeaderProps {
  query: string;
  onQueryChange: (query: string) => void;
  limit: number;
  onLimitChange: (limit: number) => void;
  forceLive: boolean;
  onForceLiveChange: (forceLive: boolean) => void;
  onSearch: (e?: React.FormEvent) => void;
  isSearching: boolean;
  onRunSinglePipeline?: () => void;
  isRunningPipeline?: boolean;
  hasSelectedJob?: boolean;
}

export function SearchHeader({
  query,
  onQueryChange,
  limit,
  onLimitChange,
  forceLive,
  onForceLiveChange,
  onSearch,
  isSearching,
  onRunSinglePipeline,
  isRunningPipeline = false,
  hasSelectedJob = false,
}: SearchHeaderProps) {
  return (
    <section className="rounded-2xl border border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] p-5 shadow-sm">
      <form onSubmit={onSearch} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Search by role or skill (e.g. Frontend Developer, Python, AI)..."
              className="pe-10"
            />
            <Search className="size-4 text-[#656C43] dark:text-[#BAC095] absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="h-11 rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-white dark:bg-[#15180E] px-3 text-xs text-[#3D4127] dark:text-[#F8F9F3] outline-none"
            >
              <option value={3}>Limit: 3</option>
              <option value={5}>Limit: 5</option>
              <option value={10}>Limit: 10</option>
            </select>

            <label className="flex items-center gap-2 text-xs text-[#4D5333] dark:text-[#DCE1C4] cursor-pointer px-2 select-none">
              <input
                type="checkbox"
                checked={forceLive}
                onChange={(e) => onForceLiveChange(e.target.checked)}
                className="rounded border-[#BAC095] text-[#636B2F] focus:ring-[#636B2F]"
              />
              <span>Live Search</span>
            </label>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button type="submit" variant="primary" disabled={isSearching}>
            {isSearching ? (
              <RefreshCw className="size-4 me-2 animate-spin" />
            ) : (
              <Search className="size-4 me-2" />
            )}
            {isSearching ? 'Searching...' : 'Search Jobs'}
          </Button>

          {hasSelectedJob && onRunSinglePipeline && (
            <Button
              type="button"
              variant="secondary"
              onClick={onRunSinglePipeline}
              disabled={isRunningPipeline}
            >
              <Sparkles className="size-4 me-1.5" />
              {isRunningPipeline ? 'Analyzing...' : 'Auto-Find Leads'}
            </Button>
          )}
        </div>
      </form>
    </section>
  );
}
