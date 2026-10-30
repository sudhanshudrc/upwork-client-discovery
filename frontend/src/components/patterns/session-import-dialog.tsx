import * as React from 'react';
import { KeyRound, ShieldCheck, RefreshCw } from 'lucide-react';
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
import { api, type SessionStatusResponse } from '@/services/api';

interface SessionImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess: (status: SessionStatusResponse) => void;
}

export function SessionImportDialog({
  open,
  onOpenChange,
  onImportSuccess,
}: SessionImportDialogProps) {
  const [userIdentifier, setUserIdentifier] = React.useState('default');
  const [cookieJson, setCookieJson] = React.useState('');
  const [isImporting, setIsImporting] = React.useState(false);
  const [isVerifying, setIsVerifying] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleImport = async () => {
    setError(null);
    if (!cookieJson.trim()) {
      setError('Please paste your Upwork cookies or session data.');
      return;
    }

    let parsedData: unknown;
    try {
      parsedData = JSON.parse(cookieJson);
    } catch {
      setError('Invalid format. Please paste a valid JSON cookies array or session file.');
      return;
    }

    setIsImporting(true);
    try {
      const result = await api.importSession(userIdentifier, parsedData);
      onImportSuccess(result);
      onOpenChange(false);
      setCookieJson('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect session');
    } finally {
      setIsImporting(false);
    }
  };

  const handleVerify = async () => {
    setError(null);
    setIsVerifying(true);
    try {
      const status = await api.verifySession(userIdentifier);
      onImportSuccess(status);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Connection check failed');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
            <DialogTitle>Upwork Connection & Cookies</DialogTitle>
          </div>
          <DialogDescription>
            Connect your Upwork session to unlock full client history and past contract feedback.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {error && (
            <div className="rounded-lg border border-[#B91C1C]/30 bg-[#FDF2F2] dark:bg-[#3D1414] p-3 text-xs text-[#B91C1C] dark:text-[#F87171]">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Profile Name
            </label>
            <Input
              value={userIdentifier}
              onChange={(e) => setUserIdentifier(e.target.value)}
              placeholder="e.g. default or your-name"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Session Cookies (JSON)
            </label>
            <textarea
              value={cookieJson}
              onChange={(e) => setCookieJson(e.target.value)}
              placeholder="Paste cookie array or browser state JSON..."
              rows={6}
              className="w-full rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-white dark:bg-[#15180E] p-3 text-xs font-mono text-[#3D4127] dark:text-[#F8F9F3] outline-none focus:border-[#636B2F] focus:ring-1 focus:ring-[#636B2F]"
            />
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleVerify}
            disabled={isVerifying}
          >
            {isVerifying ? <RefreshCw className="size-3.5 me-1 animate-spin" /> : <ShieldCheck className="size-3.5 me-1" />}
            Test Connection
          </Button>

          <Button
            type="button"
            variant="primary"
            onClick={handleImport}
            disabled={isImporting}
          >
            {isImporting ? <RefreshCw className="size-3.5 me-1 animate-spin" /> : null}
            Save & Connect
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
