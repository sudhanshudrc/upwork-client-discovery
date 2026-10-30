import { Briefcase, Compass, Users, Activity, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface StatGridProps {
  harvestedJobsCount: number;
  uniqueDomainsCount: number;
  potentialClientsCount: number;
  rateLimitHealth: string;
  activeCookiesCount?: number;
  latestDomain?: string | null;
  onOpenHarvestedJobs?: () => void;
  onOpenJobDomains?: () => void;
  onOpenPotentialClients?: () => void;
  onOpenSessionHealth?: () => void;
  className?: string;
}

export function StatGrid({
  harvestedJobsCount,
  uniqueDomainsCount,
  potentialClientsCount,
  rateLimitHealth,
  activeCookiesCount = 0,
  latestDomain,
  onOpenHarvestedJobs,
  onOpenJobDomains,
  onOpenPotentialClients,
  onOpenSessionHealth,
  className = '',
}: StatGridProps) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* 1. Harvested Jobs */}
      <Card
        onClick={onOpenHarvestedJobs}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onOpenHarvestedJobs?.()}
        className="p-4 border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] cursor-pointer hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide">
            Harvested Jobs
          </span>
          <div className="size-7 rounded-md bg-[#EFF4DC] dark:bg-[#2B3118] flex items-center justify-center text-[#636B2F] dark:text-[#D4DE95] group-hover:scale-105 transition-transform">
            <Briefcase className="size-3.5" />
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
            {harvestedJobsCount}
          </span>
          <Badge variant="brand" className="text-[10px] py-0 px-1.5 font-medium flex items-center gap-0.5">
            View All <ChevronRight className="size-2.5" />
          </Badge>
        </div>

        <div className="mt-1 text-[11px] text-[#656C43] dark:text-[#BAC095] truncate">
          All postings saved in database
        </div>
      </Card>

      {/* 2. Job Domains */}
      <Card
        onClick={onOpenJobDomains}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onOpenJobDomains?.()}
        className="p-4 border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] cursor-pointer hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide">
            Job Domains
          </span>
          <div className="size-7 rounded-md bg-[#EFF4DC] dark:bg-[#2B3118] flex items-center justify-center text-[#636B2F] dark:text-[#D4DE95] group-hover:scale-105 transition-transform">
            <Compass className="size-3.5" />
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
            {uniqueDomainsCount}
          </span>
          <Badge variant="neutral" className="text-[10px] py-0 px-1.5 font-medium flex items-center gap-0.5">
            History <ChevronRight className="size-2.5" />
          </Badge>
        </div>

        <div className="mt-1 text-[11px] text-[#656C43] dark:text-[#BAC095] truncate">
          {latestDomain ? `Latest: "${latestDomain}"` : 'Keywords searched throughout'}
        </div>
      </Card>

      {/* 3. Potential Clients */}
      <Card
        onClick={onOpenPotentialClients}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onOpenPotentialClients?.()}
        className="p-4 border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] cursor-pointer hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide">
            Potential Clients
          </span>
          <div className="size-7 rounded-md bg-[#EFF4DC] dark:bg-[#2B3118] flex items-center justify-center text-[#636B2F] dark:text-[#D4DE95] group-hover:scale-105 transition-transform">
            <Users className="size-3.5" />
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
            {potentialClientsCount}
          </span>
          <Badge variant="brand" className="text-[10px] py-0 px-1.5 font-medium flex items-center gap-0.5">
            Directory <ChevronRight className="size-2.5" />
          </Badge>
        </div>

        <div className="mt-1 text-[11px] text-[#656C43] dark:text-[#BAC095] truncate">
          Clients with discovered decision-makers
        </div>
      </Card>

      {/* 4. Rate Limit Health */}
      <Card
        onClick={onOpenSessionHealth}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onOpenSessionHealth?.()}
        className="p-4 border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] cursor-pointer hover:border-[#636B2F] dark:hover:border-[#D4DE95] hover:shadow-sm transition-all group text-left select-none"
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide">
            Rate Limit Health
          </span>
          <div className="size-7 rounded-md bg-[#EFF4DC] dark:bg-[#2B3118] flex items-center justify-center text-[#636B2F] dark:text-[#D4DE95] group-hover:scale-105 transition-transform">
            <Activity className="size-3.5" />
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline justify-between">
          <div className="flex items-center gap-1.5">
            <span
              className={`size-2.5 rounded-full ${
                rateLimitHealth === 'GREEN'
                  ? 'bg-[#636B2F]'
                  : rateLimitHealth === 'YELLOW'
                  ? 'bg-[#B37D2C]'
                  : 'bg-[#B91C1C]'
              }`}
            />
            <span className="text-lg font-bold font-mono text-[#3D4127] dark:text-[#F8F9F3]">
              {rateLimitHealth}
            </span>
          </div>
          <Badge
            variant={rateLimitHealth === 'GREEN' ? 'success' : 'warning'}
            className="text-[10px] py-0 px-1.5 font-medium flex items-center gap-0.5"
          >
            Session <ChevronRight className="size-2.5" />
          </Badge>
        </div>

        <div className="mt-1 text-[11px] text-[#656C43] dark:text-[#BAC095] truncate">
          {activeCookiesCount > 0 ? `${activeCookiesCount} cookies active` : 'Session connection status'}
        </div>
      </Card>
    </div>
  );
}
