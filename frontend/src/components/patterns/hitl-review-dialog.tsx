import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import type { IntelligenceMiningResponse } from '@/services/api';

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

interface HitlReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  intelligence: IntelligenceMiningResponse | null;
  clientName: string;
  onClientNameChange: (val: string) => void;
  companyName: string;
  onCompanyNameChange: (val: string) => void;
  targetRole: string;
  onTargetRoleChange: (val: string) => void;
  onConfirm: () => void;
  isConfirming: boolean;
}

export function HitlReviewDialog({
  open,
  onOpenChange,
  intelligence,
  clientName,
  onClientNameChange,
  companyName,
  onCompanyNameChange,
  targetRole,
  onTargetRoleChange,
  onConfirm,
  isConfirming,
}: HitlReviewDialogProps) {
  // Collect all discovered client names
  const clientNameOptions = useMemo(() => {
    const names = new Set<string>();
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
  }, [intelligence]);

  // Collect all discovered companies
  const companyOptions = useMemo(() => {
    const comps = new Set<string>();
    if (intelligence?.suggested_company_name?.trim()) {
      comps.add(intelligence.suggested_company_name.trim());
    }
    if (intelligence?.company_candidates) {
      for (const cand of intelligence.company_candidates) {
        if (cand.name?.trim()) comps.add(cand.name.trim());
      }
    }
    return Array.from(comps);
  }, [intelligence]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Client Details</DialogTitle>
          <DialogDescription>
            Select from detected entities or manually edit the client name and organization before searching LinkedIn.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Field 1: Client Name with Dropdown + Manual Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
                Client Name <span className="text-[#B91C1C]">*</span>
              </label>
              <span className="text-[10px] text-[#B91C1C] font-medium">Required</span>
            </div>

            {/* Dropdown for Discovered Names */}
            {clientNameOptions.length > 0 && (
              <div className="space-y-1">
                <select
                  aria-label="Pick from detected client names"
                  value={clientNameOptions.includes(clientName) ? clientName : ''}
                  onChange={(e) => {
                    if (e.target.value) {
                      onClientNameChange(e.target.value);
                    }
                  }}
                  className="w-full text-xs bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
                >
                  <option value="">-- Choose detected name (or type manually below) --</option>
                  {clientNameOptions.map((name) => {
                    const cand = intelligence?.client_name_candidates?.find(
                      (c) => c.name.toLowerCase() === name.toLowerCase()
                    );
                    const label = cand
                      ? `${name} (${Number(cand.confidence).toFixed(0)}% conf, ${cand.mention_count}x)`
                      : name;
                    return (
                      <option key={name} value={name}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>
            )}

            {/* Manual text input */}
            <Input
              value={clientName}
              onChange={(e) => onClientNameChange(e.target.value)}
              placeholder="e.g. Martin, Zarina, or Rupesh"
              className={!clientName.trim() ? 'border-[#B91C1C]/50 focus:border-[#B91C1C]' : ''}
              autoFocus
            />

            {/* Quick Pills if multiple names */}
            {clientNameOptions.length > 1 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Quick pick:</span>
                {clientNameOptions.map((name) => {
                  const isSelected = clientName.toLowerCase() === name.toLowerCase();
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => onClientNameChange(name)}
                      className={`text-[11px] px-2 py-0.5 rounded cursor-pointer border transition-colors ${
                        isSelected
                          ? 'bg-[#636B2F] text-white border-[#636B2F]'
                          : 'bg-[#EFF2E3] dark:bg-[#15180E] border-[#BAC095] dark:border-[#2E331E] hover:border-[#636B2F]'
                      }`}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            )}

            <p className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Target person name used for LinkedIn in-app & Google X-Ray search. You can select above or edit manually.
            </p>
          </div>

          {/* Field 2: Company with Dropdown + Manual Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
                Company / Organization
              </label>
              <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Optional</span>
            </div>

            {/* Dropdown for Discovered Companies */}
            {companyOptions.length > 0 && (
              <div className="space-y-1">
                <select
                  aria-label="Pick from detected companies"
                  value={companyOptions.includes(companyName) ? companyName : ''}
                  onChange={(e) => onCompanyNameChange(e.target.value)}
                  className="w-full text-xs bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
                >
                  <option value="">-- Choose detected company (or type manually below) --</option>
                  <option value="">None / Independent Client</option>
                  {companyOptions.map((comp) => {
                    const cand = intelligence?.company_candidates?.find(
                      (c) => c.name.toLowerCase() === comp.toLowerCase()
                    );
                    const label = cand ? `${comp} (${Number(cand.confidence).toFixed(0)}% conf)` : comp;
                    return (
                      <option key={comp} value={comp}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>
            )}

            {/* Manual text input */}
            <Input
              value={companyName}
              onChange={(e) => onCompanyNameChange(e.target.value)}
              placeholder="Leave empty if unknown or independent client"
            />
            <p className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Optional. If left blank, searches match by name and client location without company restrictions.
            </p>
          </div>

          {/* Field 3: Target Role with Dropdown + Manual Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
                Target Decision-Maker Role
              </label>
              <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Optional</span>
            </div>

            {/* Role Dropdown */}
            <div className="space-y-1">
              <select
                aria-label="Pick target role"
                value={COMMON_ROLES.includes(targetRole) ? targetRole : 'Custom'}
                onChange={(e) => {
                  if (e.target.value !== 'Custom') {
                    onTargetRoleChange(e.target.value);
                  }
                }}
                className="w-full text-xs bg-[#EFF2E3] dark:bg-[#15180E] text-[#3D4127] dark:text-[#F8F9F3] border border-[#BAC095] dark:border-[#2E331E] rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#636B2F]"
              >
                {COMMON_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
                <option value="Custom">Custom Role (Type below)</option>
              </select>
            </div>

            {/* Manual text input */}
            <Input
              value={targetRole}
              onChange={(e) => onTargetRoleChange(e.target.value)}
              placeholder="e.g. Founder, CEO, Director, CTO"
            />
          </div>

          {/* Review Quote Evidence */}
          {intelligence?.client_name_candidates?.[0]?.supporting_context && (
            <div className="p-3 rounded-lg bg-[#EFF4DC]/40 dark:bg-[#2B3118]/40 border border-[#636B2F]/30 text-xs space-y-1">
              <span className="text-[10px] font-semibold text-[#636B2F] dark:text-[#D4DE95] uppercase tracking-wide block">
                Quote from Past Freelancer Feedback:
              </span>
              <p className="italic text-[#3D4127] dark:text-[#F8F9F3]">
                &quot;{intelligence.client_name_candidates[0].supporting_context}&quot;
              </p>
            </div>
          )}

          {intelligence?.agency_detection_reason && (
            <div className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Organization type: {intelligence.agency_detection_reason}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onConfirm}
            disabled={isConfirming || !clientName.trim()}
          >
            {isConfirming ? 'Searching...' : 'Find Decision-Makers on LinkedIn'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
