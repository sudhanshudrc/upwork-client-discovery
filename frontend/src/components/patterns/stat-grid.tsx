import { Bookmark, History, Users, KeyRound, ChevronRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import type { AppPage } from '@/components/patterns/app-header';

interface StatGridProps {
  harvestedJobsCount: number;
  uniqueDomainsCount: number;
  potentialClientsCount: number;
  rateLimitHealth?: string;
  activeCookiesCount?: number;
  latestDomain?: string | null;
  activeProfile?: string;
  onNavigate: (page: AppPage) => void;
  className?: string;
}

export function StatGrid({
  harvestedJobsCount,
  uniqueDomainsCount,
  potentialClientsCount,
  activeCookiesCount = 0,
  latestDomain,
  onNavigate,
  className = '',
}: StatGridProps) {
  const isConnected = activeCookiesCount > 0;

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* 1. Saved Jobs Card */}
      <Card
        onClick={() => onNavigate('saved-jobs')}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onNavigate('saved-jobs')}
        className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Saved Jobs
          </span>
          <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition-all">
            <Bookmark className="size-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-50">
            {harvestedJobsCount}
          </span>
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex items-center group-hover:translate-x-0.5 transition-transform">
            View Page <ChevronRight className="size-3 ms-0.5" />
          </span>
        </div>

        <div className="mt-1 text-xs text-slate-500 truncate">
          Total job postings collected
        </div>
      </Card>

      {/* 2. Search History Card */}
      <Card
        onClick={() => onNavigate('search-history')}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onNavigate('search-history')}
        className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Search History
          </span>
          <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition-all">
            <History className="size-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-50">
            {uniqueDomainsCount}
          </span>
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex items-center group-hover:translate-x-0.5 transition-transform">
            View Page <ChevronRight className="size-3 ms-0.5" />
          </span>
        </div>

        <div className="mt-1 text-xs text-slate-500 truncate">
          {latestDomain ? `Latest: "${latestDomain}"` : 'Saved search queries'}
        </div>
      </Card>

      {/* 3. Discovered Clients Card */}
      <Card
        onClick={() => onNavigate('clients')}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onNavigate('clients')}
        className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Discovered Clients
          </span>
          <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition-all">
            <Users className="size-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-50">
            {potentialClientsCount}
          </span>
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex items-center group-hover:translate-x-0.5 transition-transform">
            View Page <ChevronRight className="size-3 ms-0.5" />
          </span>
        </div>

        <div className="mt-1 text-xs text-slate-500 truncate">
          Businesses & verified decision-makers
        </div>
      </Card>

      {/* 4. Upwork Connection Status Card */}
      <Card
        onClick={() => onNavigate('connection')}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onNavigate('connection')}
        className={`p-4 border bg-white dark:bg-slate-900 cursor-pointer hover:shadow-md transition-all group text-left select-none ${
          isConnected
            ? 'border-slate-200 dark:border-slate-800 hover:border-emerald-500'
            : 'border-red-300 dark:border-red-800/80 bg-red-50/20 dark:bg-red-950/20 hover:border-red-500'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Upwork Connection
          </span>
          <div
            className={`size-8 rounded-lg flex items-center justify-center transition-all ${
              isConnected
                ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 group-hover:bg-emerald-600 group-hover:text-white'
                : 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400 group-hover:bg-red-600 group-hover:text-white'
            }`}
          >
            <KeyRound className="size-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <div className="flex items-center gap-1.5">
            {isConnected ? (
              <CheckCircle2 className="size-4 text-emerald-600" />
            ) : (
              <AlertCircle className="size-4 text-red-600" />
            )}
            <span
              className={`text-lg font-bold ${
                isConnected ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'
              }`}
            >
              {isConnected ? 'Connected' : 'Cookies Needed'}
            </span>
          </div>

          <span
            className={`text-xs font-semibold flex items-center group-hover:translate-x-0.5 transition-transform ${
              isConnected ? 'text-emerald-600' : 'text-red-600'
            }`}
          >
            Manage <ChevronRight className="size-3 ms-0.5" />
          </span>
        </div>

        <div className="mt-1 text-xs text-slate-500 truncate">
          {isConnected
            ? `${activeCookiesCount} active cookies loaded`
            : 'Action required: click to connect'}
        </div>
      </Card>
    </div>
  );
}
