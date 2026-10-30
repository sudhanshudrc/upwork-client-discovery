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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Client Details</DialogTitle>
          <DialogDescription>
            Review the client name and organization details found in Upwork feedback before searching LinkedIn.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
                Client Name <span className="text-[#B91C1C]">*</span>
              </label>
              <span className="text-[10px] text-[#B91C1C] font-medium">Required</span>
            </div>
            <Input
              value={clientName}
              onChange={(e) => onClientNameChange(e.target.value)}
              placeholder="e.g. Martin or Zarina"
              className={!clientName.trim() ? 'border-[#B91C1C]/50 focus:border-[#B91C1C]' : ''}
              autoFocus
            />
            <p className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              The client&apos;s first or full name is required to match profiles on LinkedIn.
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
                Company / Organization
              </label>
              <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Optional</span>
            </div>
            <Input
              value={companyName}
              onChange={(e) => onCompanyNameChange(e.target.value)}
              placeholder="Leave empty if unknown or independent client"
            />
            <p className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Optional. If left blank, searches match by name and client location without company restrictions.
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
                Target Decision-Maker Role
              </label>
              <span className="text-[10px] text-[#656C43] dark:text-[#BAC095]">Optional</span>
            </div>
            <Input
              value={targetRole}
              onChange={(e) => onTargetRoleChange(e.target.value)}
              placeholder="e.g. Founder, CEO, Director, CTO"
            />
          </div>

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
