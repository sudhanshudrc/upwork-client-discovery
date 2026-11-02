import { useMemo } from 'react';
import { UserCheck, Building2, Briefcase, ShieldAlert, Quote, MapPin } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { IntelligenceMiningResponse, ConfirmedIntelligence } from '@/services/api';

const COMMON_ROLES = [
  'CTO',
  'Founder',
  'Co-Founder',
  'CEO',
  'VP of Engineering',
  'Director of Technology',
  'Head of Product',
  'Owner',
];

interface IntelligenceCardProps {
  intelligence: IntelligenceMiningResponse | null;
  confirmedIntelligence: ConfirmedIntelligence | null;
  clientLocation?: string | null;
  onOpenReviewDialog: () => void;
  onDiscoverLeads?: () => void;
  isDiscovering?: boolean;
  selectedClientName?: string;
  onSelectClientName?: (name: string) => void;
  selectedCompanyName?: string;
  onSelectCompanyName?: (company: string) => void;
  selectedRole?: string;
  onSelectRole?: (role: string) => void;
}

export function IntelligenceCard({
  intelligence,
  confirmedIntelligence,
  clientLocation,
  onOpenReviewDialog,
  onDiscoverLeads,
  isDiscovering = false,
  selectedClientName,
  onSelectClientName,
  selectedCompanyName,
  onSelectCompanyName,
  selectedRole,
  onSelectRole,
}: IntelligenceCardProps) {
  // Collect all unique client names discovered
  const clientNameOptions = useMemo(() => {
    const names = new Set<string>();
    if (selectedClientName?.trim()) {
      names.add(selectedClientName.trim());
    }
    if (confirmedIntelligence?.confirmed_client_name) {
      for (const n of confirmedIntelligence.confirmed_client_name.split(',')) {
        if (n.trim()) names.add(n.trim());
      }
    }
    if (intelligence?.suggested_client_names) {
      for (const n of intelligence.suggested_client_names) {
        if (n?.trim()) names.add(n.trim());
      }
    }
    if (intelligence?.client_name_candidates) {
      for (const cand of intelligence.client_name_candidates) {
        if (cand.name?.trim()) names.add(cand.name.trim());
      }
    }
    if (intelligence?.suggested_client_name) {
      for (const n of intelligence.suggested_client_name.split(',')) {
        if (n.trim()) names.add(n.trim());
      }
    }
    return Array.from(names);
  }, [selectedClientName, confirmedIntelligence, intelligence]);

  // Collect all unique company options
  const companyOptions = useMemo(() => {
    const comps = new Set<string>();
    if (selectedCompanyName?.trim()) {
      comps.add(selectedCompanyName.trim());
    }
    if (confirmedIntelligence?.confirmed_company_name?.trim()) {
      comps.add(confirmedIntelligence.confirmed_company_name.trim());
    }
    if (intelligence?.suggested_company_name?.trim()) {
      comps.add(intelligence.suggested_company_name.trim());
    }
    if (intelligence?.company_candidates) {
      for (const cand of intelligence.company_candidates) {
        if (cand.name?.trim()) comps.add(cand.name.trim());
      }
    }
    return Array.from(comps);
  }, [selectedCompanyName, confirmedIntelligence, intelligence]);

  // Collect role options
  const roleOptions = useMemo(() => {
    const roles = new Set<string>(COMMON_ROLES);
    if (selectedRole?.trim()) {
      roles.add(selectedRole.trim());
    }
    if (confirmedIntelligence?.target_role?.trim()) {
      roles.add(confirmedIntelligence.target_role.trim());
    }
    if (intelligence?.suggested_role?.trim()) {
      roles.add(intelligence.suggested_role.trim());
    }
    return Array.from(roles);
  }, [selectedRole, confirmedIntelligence, intelligence]);

  const activeClientName =
    selectedClientName ||
    confirmedIntelligence?.confirmed_client_name ||
    clientNameOptions[0] ||
    null;

  const activeCompanyName =
    selectedCompanyName !== undefined
      ? selectedCompanyName
      : confirmedIntelligence?.confirmed_company_name ||
        intelligence?.suggested_company_name ||
        '';

  const activeRole =
    selectedRole ||
    confirmedIntelligence?.target_role ||
    intelligence?.suggested_role ||
    'CTO';

  const confidence =
    confirmedIntelligence?.name_confidence ||
    intelligence?.client_name_candidates?.find(
      (c) => c.name.toLowerCase() === activeClientName?.toLowerCase()
    )?.confidence ||
    intelligence?.client_name_candidates?.[0]?.confidence ||
    null;

  const companyConfidence = intelligence?.company_candidates?.find(
    (c) => c.name.toLowerCase() === activeCompanyName?.toLowerCase()
  )?.confidence;

  const isApproved =
    confirmedIntelligence?.approval_status === 'APPROVED' ||
    intelligence?.approval_status === 'APPROVED';

  if (!activeClientName && !intelligence && clientNameOptions.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-[#656C43] dark:text-[#BAC095] border border-dashed border-[#BAC095] rounded-lg space-y-3">
        <div>No client identity verified yet for this posting.</div>
        <Button variant="secondary" size="sm" onClick={onOpenReviewDialog}>
          <UserCheck className="size-3.5 me-1" />
          Identify Client Details
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Status & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#EFF2E3] dark:border-[#2E331E]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
            Client Verification & Profile
          </span>
          <Badge variant={isApproved ? 'success' : 'warning'}>
            {isApproved ? 'Verified Client' : 'Needs Confirmation'}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onOpenReviewDialog}>
            Edit Details
          </Button>

          {onDiscoverLeads && (
            <Button
              variant="primary"
              size="sm"
              onClick={onDiscoverLeads}
              disabled={isDiscovering || !activeClientName}
            >
              {isDiscovering ? 'Searching...' : 'Find Decision-Makers on LinkedIn'}
            </Button>
          )}
        </div>
      </div>

      {/* Target Location Banner */}
      {clientLocation && (
        <div className="p-3 rounded-lg border border-[#636B2F]/30 bg-[#EFF4DC]/40 dark:bg-[#2B3118]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <MapPin className="size-4 text-[#636B2F] dark:text-[#D4DE95] shrink-0" />
            <span className="font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
              Location for LinkedIn Search:
            </span>
            <span className="text-[#636B2F] dark:text-[#D4DE95] font-bold">
              {clientLocation}
            </span>
          </div>
          <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
            Matches local metro area
          </span>
        </div>
      )}

      {/* Primary Extracted Entities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Entity 1: Client Decision-Maker */}
        <Card className="p-4 border-[#636B2F]/30 bg-[#EFF4DC]/30 dark:bg-[#2B3118]/30 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-[#4D5333] dark:text-[#DCE1C4] flex items-center gap-1">
              <UserCheck className="size-3.5 text-[#636B2F] dark:text-[#D4DE95]" />
              Identified Client Name
            </span>
            {confidence && (
              <Badge variant="tier-a" className="text-[10px]">
                {Number(confidence).toFixed(0)}% Conf.
              </Badge>
            )}
          </div>

          {clientNameOptions.length > 1 ? (
            <div className="space-y-1">
              <select
                aria-label="Select identified client name"
                value={activeClientName || ''}
                onChange={(e) => onSelectClientName?.(e.target.value)}
                className="w-full text-sm font-bold bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
              >
                {clientNameOptions.map((name) => {
                  const cand = intelligence?.client_name_candidates?.find(
                    (c) => c.name.toLowerCase() === name.toLowerCase()
                  );
                  const label = cand
                    ? `${name} (${Number(cand.confidence).toFixed(0)}%, ${cand.mention_count}x)`
                    : name;
                  return (
                    <option key={name} value={name}>
                      {label}
                    </option>
                  );
                })}
              </select>
              <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
                {clientNameOptions.length} names detected (select active target)
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="text-base font-bold text-[#3D4127] dark:text-[#F8F9F3]">
                {activeClientName || 'Not detected'}
              </div>
              <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
                Found in past freelancer reviews
              </div>
            </div>
          )}
        </Card>

        {/* Entity 2: Company / Organization */}
        <Card className="p-4 border-[#BAC095] dark:border-[#2E331E] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-[#4D5333] dark:text-[#DCE1C4] flex items-center gap-1">
              <Building2 className="size-3.5 text-[#636B2F] dark:text-[#D4DE95]" />
              Company / Business
            </span>
            {companyConfidence && (
              <Badge variant="brand" className="text-[10px]">
                {Number(companyConfidence).toFixed(0)}% Conf.
              </Badge>
            )}
          </div>

          {companyOptions.length > 1 ? (
            <div className="space-y-1">
              <select
                aria-label="Select company or business"
                value={activeCompanyName || ''}
                onChange={(e) => onSelectCompanyName?.(e.target.value)}
                className="w-full text-sm font-bold bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
              >
                <option value="">None / Independent Client</option>
                {companyOptions.map((comp) => {
                  const cand = intelligence?.company_candidates?.find(
                    (c) => c.name.toLowerCase() === comp.toLowerCase()
                  );
                  const label = cand
                    ? `${comp} (${Number(cand.confidence).toFixed(0)}%)`
                    : comp;
                  return (
                    <option key={comp} value={comp}>
                      {label}
                    </option>
                  );
                })}
              </select>
              <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
                Extracted from job posting & past titles
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="text-base font-bold text-[#3D4127] dark:text-[#F8F9F3]">
                {activeCompanyName || 'Not detected'}
              </div>
              <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
                Extracted from job posting
              </div>
            </div>
          )}
        </Card>

        {/* Entity 3: Target Role */}
        <Card className="p-4 border-[#BAC095] dark:border-[#2E331E] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-[#4D5333] dark:text-[#DCE1C4] flex items-center gap-1">
              <Briefcase className="size-3.5 text-[#636B2F] dark:text-[#D4DE95]" />
              Target Role
            </span>
            <Badge variant="neutral" className="text-[10px]">
              Active Role
            </Badge>
          </div>

          <div className="space-y-1">
            <select
              aria-label="Select target role"
              value={activeRole}
              onChange={(e) => onSelectRole?.(e.target.value)}
              className="w-full text-sm font-bold bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
            >
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
            <div className="text-[10px] text-[#656C43] dark:text-[#BAC095]">
              Target Seniority for LinkedIn Search
            </div>
          </div>
        </Card>
      </div>

      {/* Review Evidence Snippets */}
      {(confirmedIntelligence?.name_evidence_snippet ||
        intelligence?.client_name_candidates?.[0]?.supporting_context) && (
        <div className="p-3.5 rounded-lg border border-[#636B2F]/30 bg-[#EFF4DC]/40 dark:bg-[#2B3118]/40 text-xs space-y-1">
          <div className="font-semibold text-[#636B2F] dark:text-[#D4DE95] flex items-center gap-1.5">
            <Quote className="size-3.5" />
            Freelancer Review Quote:
          </div>
          <p className="italic text-[#3D4127] dark:text-[#F8F9F3] ps-2 border-l-2 border-[#636B2F]">
            &quot;
            {confirmedIntelligence?.name_evidence_snippet ||
              intelligence?.client_name_candidates?.[0]?.supporting_context}
            &quot;
          </p>
        </div>
      )}

      {/* Discovered Candidate Entities List */}
      {intelligence?.client_name_candidates && intelligence.client_name_candidates.length > 1 && (
        <Card className="p-3.5 space-y-2">
          <span className="text-[11px] font-semibold text-[#656C43] dark:text-[#BAC095] uppercase tracking-wide block">
            Click to switch target decision maker ({intelligence.client_name_candidates.length} detected)
          </span>
          <div className="flex flex-wrap gap-2">
            {intelligence.client_name_candidates.map((cand, idx) => {
              const isSelected = activeClientName?.toLowerCase() === cand.name.toLowerCase();
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSelectClientName?.(cand.name)}
                  className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-colors cursor-pointer border ${
                    isSelected
                      ? 'bg-[#636B2F] text-white border-[#636B2F]'
                      : 'bg-[#EFF2E3] dark:bg-[#15180E] border-[#BAC095] dark:border-[#2E331E] hover:border-[#636B2F]'
                  }`}
                >
                  <span className="font-semibold">
                    {cand.name}
                  </span>
                  <span className={`text-[10px] ${isSelected ? 'text-[#EFF4DC]' : 'text-[#656C43] dark:text-[#BAC095]'}`}>
                    ({Number(cand.confidence).toFixed(0)}%, {cand.mention_count}x)
                  </span>
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* Agency Detection Check */}
      <div className="p-3 rounded-lg border border-[#E1E4D3] dark:border-[#2E331E] bg-[#EFF2E3] dark:bg-[#15180E] flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
          <span className="text-[#4D5333] dark:text-[#DCE1C4]">
            Hiring Organization Type:
          </span>
        </div>
        <span className="font-medium text-[#3D4127] dark:text-[#F8F9F3]">
          {intelligence?.agency_detection_reason || 'Direct Client (Not an agency)'}
        </span>
      </div>
    </div>
  );
}
