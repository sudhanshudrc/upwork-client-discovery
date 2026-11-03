import * as React from 'react';
import {
  KeyRound,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  User,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  api,
  type SessionStatusResponse,
} from '@/services/api';

interface VerificationFeedback {
  status: 'SUCCESS' | 'FAILED';
  message: string;
  rateLimitHealth?: string;
  profileTested: string;
}

interface SessionImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess: (status: SessionStatusResponse, profile: string) => void;
  currentProfile?: string;
  onProfileChange?: (profile: string) => void;
}

export function SessionImportDialog({
  open,
  onOpenChange,
  onImportSuccess,
  currentProfile = 'default',
  onProfileChange,
}: SessionImportDialogProps) {
  const [cookieJson, setCookieJson] = React.useState<string>('');
  const [isImporting, setIsImporting] = React.useState<boolean>(false);
  const [isVerifying, setIsVerifying] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [verifyFeedback, setVerifyFeedback] = React.useState<VerificationFeedback | null>(null);

  const cleanUser = currentProfile || 'default';

  // Clear state when dialog opens or profile changes
  React.useEffect(() => {
    if (open) {
      setError(null);
      setVerifyFeedback(null);
    }
  }, [open, currentProfile]);

  const handleImport = async () => {
    setError(null);
    setVerifyFeedback(null);

    const trimmedInput = cookieJson.trim();
    if (!trimmedInput) {
      setError('Please paste your Upwork cookies or session data.');
      return;
    }

    let parsedData: unknown;
    try {
      parsedData = JSON.parse(trimmedInput);
    } catch {
      // If not JSON, check if it's a semicolon-delimited cookie string
      if (trimmedInput.includes('=')) {
        parsedData = trimmedInput;
      } else {
        setError('Invalid format. Please paste a valid JSON cookie export or raw cookie string.');
        return;
      }
    }

    setIsImporting(true);
    try {
      const result = await api.importSession(cleanUser, parsedData);
      onProfileChange?.(cleanUser);
      onImportSuccess(result, cleanUser);
      setCookieJson('');
      setVerifyFeedback({
        status: 'SUCCESS',
        message: result.message || `Session saved and encrypted for '${cleanUser}'.`,
        rateLimitHealth: result.rate_limit_health,
        profileTested: cleanUser,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect session');
    } finally {
      setIsImporting(false);
    }
  };

  const handleVerify = async () => {
    setError(null);
    setVerifyFeedback(null);
    setIsVerifying(true);

    try {
      // If the user entered cookies into the box without clicking Save first, save & verify
      if (cookieJson.trim()) {
        let parsedData: unknown;
        try {
          parsedData = JSON.parse(cookieJson.trim());
        } catch {
          if (cookieJson.trim().includes('=')) {
            parsedData = cookieJson.trim();
          }
        }
        if (parsedData) {
          await api.importSession(cleanUser, parsedData);
          setCookieJson('');
        }
      }

      const status = await api.verifySession(cleanUser);
      onProfileChange?.(cleanUser);
      onImportSuccess(status, cleanUser);

      if (status.is_authenticated) {
        setVerifyFeedback({
          status: 'SUCCESS',
          message: status.message || `Active authenticated session verified for '${cleanUser}'.`,
          rateLimitHealth: status.rate_limit_health,
          profileTested: cleanUser,
        });
      } else {
        setVerifyFeedback({
          status: 'FAILED',
          message: status.message || `Probe failed: session for '${cleanUser}' is expired or blocked.`,
          rateLimitHealth: status.rate_limit_health,
          profileTested: cleanUser,
        });
      }
    } catch (err: unknown) {
      setVerifyFeedback({
        status: 'FAILED',
        message: err instanceof Error ? err.message : 'Connection probe failed to reach backend or Upwork.',
        profileTested: cleanUser,
      });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <KeyRound className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
              <DialogTitle>Upwork Connection & Cookies</DialogTitle>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#EFF4DC] dark:bg-[#2B3118] text-[11px] font-medium text-[#4D5333] dark:text-[#DCE1C4]">
              <User className="size-3 text-[#636B2F] dark:text-[#D4DE95]" />
              <span>Active: <strong className="font-semibold">{cleanUser}</strong></span>
            </div>
          </div>
          <DialogDescription>
            Import encrypted cookies and verify connection liveness for your isolated profile.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Error Banner */}
          {error && (
            <div className="rounded-lg border border-[#B91C1C]/30 bg-[#FDF2F2] dark:bg-[#3D1414] p-3 text-xs text-[#B91C1C] dark:text-[#F87171] flex items-start gap-2">
              <AlertTriangle className="size-4 shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold">Import Error</div>
                <div>{error}</div>
              </div>
            </div>
          )}

          {/* Live In-Progress Testing Banner */}
          {isVerifying && (
            <div className="rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-[#F8F9F3] dark:bg-[#1C2012] p-3 text-xs text-[#4D5333] dark:text-[#DCE1C4] flex items-center gap-2.5 animate-pulse">
              <RefreshCw className="size-4 animate-spin text-[#636B2F] dark:text-[#D4DE95]" />
              <div>
                <div className="font-semibold">Testing Connection</div>
                <div className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
                  Executing live Playwright probe to Upwork search for &apos;{cleanUser}&apos;...
                </div>
              </div>
            </div>
          )}

          {/* Verification Feedback (Confirmation of Successful or Unsuccessful) */}
          {verifyFeedback && !isVerifying && (
            <div
              className={`rounded-lg border p-3.5 text-xs flex items-start gap-2.5 ${
                verifyFeedback.status === 'SUCCESS'
                  ? 'border-[#86EFAC] bg-[#F0FDF4] text-[#166534] dark:border-[#22C55E]/40 dark:bg-[#142B1A] dark:text-[#4ADE80]'
                  : 'border-[#FCA5A5] bg-[#FEF2F2] text-[#991B1B] dark:border-[#EF4444]/40 dark:bg-[#381616] dark:text-[#F87171]'
              }`}
            >
              {verifyFeedback.status === 'SUCCESS' ? (
                <CheckCircle2 className="size-4 shrink-0 mt-0.5 text-[#16A34A] dark:text-[#4ADE80]" />
              ) : (
                <AlertTriangle className="size-4 shrink-0 mt-0.5 text-[#DC2626] dark:text-[#F87171]" />
              )}
              <div className="space-y-1 flex-1">
                <div className="font-bold flex items-center justify-between">
                  <span>
                    {verifyFeedback.status === 'SUCCESS'
                      ? 'Connection Successful - Session Active'
                      : 'Connection Test Failed - Action Required'}
                  </span>
                  {verifyFeedback.rateLimitHealth && (
                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${
                        verifyFeedback.rateLimitHealth === 'GREEN'
                          ? 'bg-[#DCFCE7] text-[#166534] dark:bg-[#1E3A24] dark:text-[#86EFAC]'
                          : 'bg-[#FEF3C7] text-[#92400E] dark:bg-[#3A2D13] dark:text-[#FCD34D]'
                      }`}
                    >
                      Health: {verifyFeedback.rateLimitHealth}
                    </span>
                  )}
                </div>
                <div className="text-[11px] leading-relaxed">
                  {verifyFeedback.message}
                </div>
                <div className="text-[10px] opacity-80 pt-0.5">
                  Target Profile: <strong>{verifyFeedback.profileTested}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Locked Target Account Display */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Target Account Profile
            </label>
            <div className="flex items-center gap-2 rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-[#F8F9F3] dark:bg-[#1C2012] px-3 py-2 text-xs font-medium text-[#3D4127] dark:text-[#F8F9F3]">
              <User className="size-3.5 text-[#636B2F] dark:text-[#D4DE95]" />
              <span className="font-semibold">{cleanUser}</span>
              <span className="ms-auto text-[10px] text-[#656C43] dark:text-[#BAC095]">Locked to current session</span>
            </div>
            <p className="text-[11px] text-[#656C43] dark:text-[#BAC095]">
              Your Upwork cookies are encrypted with AES-256-GCM and strictly isolated to this account.
            </p>
          </div>

          {/* Cookie Payload Textarea */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Session Cookies (JSON or Raw Cookie String)
            </label>
            <textarea
              value={cookieJson}
              onChange={(e) => {
                setCookieJson(e.target.value);
                setVerifyFeedback(null);
              }}
              placeholder="Paste cookie array JSON, Playwright state JSON, or raw cookie header string (e.g. oauth2_global_js_token=...; master_access_token=...)"
              rows={5}
              className="w-full rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-white dark:bg-[#15180E] p-3 text-xs font-mono text-[#3D4127] dark:text-[#F8F9F3] outline-none border focus:border-[#636B2F] focus:ring-1 focus:ring-[#636B2F]"
            />
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleVerify}
            disabled={isVerifying || isImporting}
          >
            {isVerifying ? (
              <RefreshCw className="size-3.5 me-1 animate-spin" />
            ) : (
              <ShieldCheck className="size-3.5 me-1" />
            )}
            Test Connection
          </Button>

          <Button
            type="button"
            variant="primary"
            onClick={handleImport}
            disabled={isImporting || isVerifying || !cookieJson.trim()}
          >
            {isImporting ? <RefreshCw className="size-3.5 me-1 animate-spin" /> : null}
            Save & Connect
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
