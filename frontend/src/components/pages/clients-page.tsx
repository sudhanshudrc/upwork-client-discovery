import * as React from 'react';
import {
  Users,
  Search,
  ArrowLeft,
  ExternalLink,
  MapPin,
  Building,
  UserCheck,
  ChevronRight,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardClients } from '@/hooks/use-dashboard';
import type { DashboardClientItem, DiscoveredCandidateSummary } from '@/services/api';

interface ClientsPageProps {
  onSelectJob: (jobUid: string) => void;
  onBackToOverview: () => void;
}

export function ClientsPage({ onSelectJob, onBackToOverview }: ClientsPageProps) {
  const { data: clients, isLoading } = useDashboardClients();
  const [filterQuery, setFilterQuery] = React.useState('');

  const filteredClients = React.useMemo(() => {
    if (!clients) return [];
    if (!filterQuery.trim()) return clients;
    const q = filterQuery.toLowerCase();
    return clients.filter(
      (c) =>
        (c.client_name && c.client_name.toLowerCase().includes(q)) ||
        (c.company_name && c.company_name.toLowerCase().includes(q)) ||
        (c.location && c.location.toLowerCase().includes(q)) ||
        (c.target_role && c.target_role.toLowerCase().includes(q))
    );
  }, [clients, filterQuery]);

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
              <Users className="size-5 text-blue-600" />
              Discovered Clients Directory
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Verified business profiles and decision-makers discovered from Upwork job contracts
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
            placeholder="Search clients, company, or role..."
            className="w-full h-9 pl-9 pr-3 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Clients Listing */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-44 w-full rounded-xl" />
          ))}
        </div>
      ) : filteredClients.length === 0 ? (
        <Card className="p-16 text-center space-y-3">
          <Users className="size-10 mx-auto text-slate-300 dark:text-slate-600" />
          <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
            No discovered clients yet
          </div>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            When you inspect jobs and find client contacts, they will appear here in your directory.
          </p>
          <Button variant="primary" size="sm" onClick={onBackToOverview}>
            Find Clients from Jobs
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredClients.map((client: DashboardClientItem) => (
            <Card
              key={client.client_id}
              className="p-5 flex flex-col justify-between hover:border-slate-300 dark:hover:border-slate-700 transition-all"
            >
              <div className="space-y-3">
                {/* Header: Client & Company */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-50 flex items-center gap-1.5">
                      <UserCheck className="size-4 text-blue-600" />
                      <span>{client.client_name || 'Anonymous Client'}</span>
                    </h3>
                    {client.company_name && (
                      <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                        <Building className="size-3" />
                        <span>{client.company_name}</span>
                      </div>
                    )}
                  </div>

                  {client.location && (
                    <Badge variant="neutral" className="text-xs flex items-center gap-1">
                      <MapPin className="size-3 text-slate-400" />
                      <span>{client.location}</span>
                    </Badge>
                  )}
                </div>

                {/* Job Info */}
                {client.origin_job && (
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-1">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
                      Associated Job Posting
                    </div>
                    <div className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">
                      {client.origin_job.title}
                    </div>
                  </div>
                )}

                {/* Scored Decision-Makers / Candidates */}
                {client.candidates && client.candidates.length > 0 ? (
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide flex items-center justify-between">
                      <span>Found Contacts</span>
                      <span className="text-blue-600 font-bold">{client.candidates.length}</span>
                    </div>
                    <div className="space-y-1.5">
                      {client.candidates.slice(0, 2).map((c: DiscoveredCandidateSummary) => (
                        <div
                          key={c.id}
                          className="flex items-center justify-between p-2 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs"
                        >
                          <div>
                            <span className="font-semibold text-slate-900 dark:text-slate-100">
                              {c.full_name}
                            </span>
                            {c.headline && (
                              <p className="text-[11px] text-slate-500 truncate max-w-xs">
                                {c.headline}
                              </p>
                            )}
                          </div>
                          {c.linkedin_url && (
                            <a
                              href={c.linkedin_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-600 hover:text-blue-700 text-[11px] font-medium flex items-center gap-0.5 shrink-0"
                            >
                              <span>LinkedIn</span>
                              <ExternalLink className="size-3" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 italic">
                    Ready to search decision-makers on LinkedIn
                  </div>
                )}
              </div>

              {/* Action Footer */}
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">
                  Target Role: <strong className="text-slate-700 dark:text-slate-300">{client.target_role || 'Decision-Maker'}</strong>
                </span>

                {client.origin_job && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      onSelectJob(client.origin_job.job_uid);
                      onBackToOverview();
                    }}
                    className="text-xs flex items-center gap-1"
                  >
                    <span>View Job & Leads</span>
                    <ChevronRight className="size-3.5" />
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
