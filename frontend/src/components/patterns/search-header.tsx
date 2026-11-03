import * as React from 'react';
import { Search, RefreshCw, FileSpreadsheet } from 'lucide-react';
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
  exportBatchUrl?: string;
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
  exportBatchUrl,
}: SearchHeaderProps) {
  return (
    <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
      <form onSubmit={onSearch} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Search by role or skill (e.g. Frontend Developer, Python, AI)..."
              className="pe-10"
            />
            <Search className="size-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500"
            >
              <option value={3}>Limit: 3</option>
              <option value={5}>Limit: 5</option>
              <option value={10}>Limit: 10</option>
            </select>

            <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer px-2 select-none">
              <input
                type="checkbox"
                checked={forceLive}
                onChange={(e) => onForceLiveChange(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Live Search</span>
            </label>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button type="submit" variant="primary" disabled={isSearching} className="h-10">
            {isSearching ? (
              <RefreshCw className="size-4 me-2 animate-spin" />
            ) : (
              <Search className="size-4 me-2" />
            )}
            {isSearching ? 'Searching...' : 'Search Jobs'}
          </Button>

          {exportBatchUrl && (
            <a
              href={exportBatchUrl}
              download
              className="inline-flex items-center justify-center h-10 px-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              title={`Download leads for "${query}" as an Excel spreadsheet`}
            >
              <FileSpreadsheet className="size-3.5 me-1.5 text-emerald-600" />
              <span>Export Excel</span>
            </a>
          )}
        </div>
      </form>
    </section>
  );
}
