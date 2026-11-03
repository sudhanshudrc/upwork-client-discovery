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
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Review Client Details</DialogTitle>
          <DialogDescription>
            Verify the client name and target role before searching LinkedIn.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Client Name Input & Suggestions */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Client Name
            </label>
            <Input
              value={clientName}
              onChange={(e) => onClientNameChange(e.target.value)}
              placeholder="e.g. John Smith"
            />
            {clientNameOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className="text-[10px] text-slate-400 self-center">Suggestions:</span>
                {clientNameOptions.map((name) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => onClientNameChange(name)}
                    className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-600 transition-colors border border-slate-200 dark:border-slate-700"
                  >
                    {name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Company Name Input & Suggestions */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Company Name (Optional)
            </label>
            <Input
              value={companyName}
              onChange={(e) => onCompanyNameChange(e.target.value)}
              placeholder="e.g. Acme Corporation"
            />
            {companyOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className="text-[10px] text-slate-400 self-center">Suggestions:</span>
                {companyOptions.map((comp) => (
                  <button
                    key={comp}
                    type="button"
                    onClick={() => onCompanyNameChange(comp)}
                    className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-600 transition-colors border border-slate-200 dark:border-slate-700"
                  >
                    {comp}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Target Role Input & Common Roles */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Target Role
            </label>
            <Input
              value={targetRole}
              onChange={(e) => onTargetRoleChange(e.target.value)}
              placeholder="e.g. CTO, Founder, VP Engineering"
            />
            <div className="flex flex-wrap gap-1.5 pt-1">
              <span className="text-[10px] text-slate-400 self-center">Common:</span>
              {COMMON_ROLES.slice(0, 5).map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => onTargetRoleChange(role)}
                  className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-600 transition-colors border border-slate-200 dark:border-slate-700"
                >
                  {role}
                </button>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isConfirming}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onConfirm}
            disabled={isConfirming || !clientName.trim()}
          >
            {isConfirming ? 'Searching LinkedIn...' : 'Confirm & Search Leads'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
