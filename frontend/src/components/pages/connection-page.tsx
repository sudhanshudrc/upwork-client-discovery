import * as React from 'react';
import {
  KeyRound,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  ExternalLink,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, type SessionStatusResponse } from '@/services/api';
import { useAuth } from '@/context/auth-context';

interface ConnectionPageProps {
  currentProfile: string;
  sessionStatus?: SessionStatusResponse | null;
  onRefreshSession: () => void;
  onBackToOverview: () => void;
}

export function ConnectionPage({
  currentProfile,
  sessionStatus,
  onRefreshSession,
  onBackToOverview,
}: ConnectionPageProps) {
  const { user } = useAuth();
  const [cookieJson, setCookieJson] = React.useState('');
  const [decryptPassword, setDecryptPassword] = React.useState('Drc@1234');
  const [isSaving, setIsSaving] = React.useState(false);
  const [isTesting, setIsTesting] = React.useState(false);
  const [feedback, setFeedback] = React.useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const isEncryptedCookieFile = React.useMemo(() => {
    const trimmed = cookieJson.trim();
    return (
      (trimmed.includes('"version": 2') || trimmed.includes('"version":2')) &&
      trimmed.includes('"data"')
    );
  }, [cookieJson]);

  const activeAccount = user ? user.email : currentProfile;
  const isConnected = Boolean(sessionStatus?.is_authenticated);

  const cookieMatch =
    sessionStatus?.message?.match(/with (\d+) cookies/i) ||
    sessionStatus?.message?.match(/\((\d+) cookies\)/i);
  const cookieCount = cookieMatch
    ? Number(cookieMatch[1])
    : (user?.upwork_cookie_count || (sessionStatus?.is_authenticated ? 79 : 0));

  const handleSaveCookies = async () => {
    setFeedback(null);
    const trimmed = cookieJson.trim();
    if (!trimmed) {
      setFeedback({
        type: 'error',
        message: 'Please paste your cookie data into the box before saving.',
      });
      return;
    }

    if (isEncryptedCookieFile && !decryptPassword.trim()) {
      setFeedback({
        type: 'error',
        message: 'This cookie file is encrypted. Please enter the password you used during export.',
      });
      return;
    }

    let parsedData: unknown;
    try {
      parsedData = JSON.parse(trimmed);
    } catch {
      if (trimmed.includes('=')) {
        parsedData = trimmed;
      } else {
        setFeedback({
          type: 'error',
          message: 'Invalid cookie format. Please paste JSON format from your browser Cookie Editor.',
        });
        return;
      }
    }

    setIsSaving(true);
    try {
      const res = await api.importSession(activeAccount, parsedData, isEncryptedCookieFile ? decryptPassword.trim() : undefined);
      setCookieJson('');
      onRefreshSession();
      setFeedback({
        type: 'success',
        message: res.message || 'Upwork cookies saved successfully! Testing connection now...',
      });
      // Automatically test connection after saving
      handleTestConnection();
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save cookies. Please try again.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setFeedback(null);
    setIsTesting(true);

    try {
      const status = await api.verifySession(activeAccount);
      onRefreshSession();

      if (status.is_authenticated) {
        setFeedback({
          type: 'success',
          message: 'Connection verified successfully! Your account is ready for searches.',
        });
      } else {
        setFeedback({
          type: 'error',
          message: status.message || 'Verification failed. Your cookies may be expired or invalid. Please re-export.',
        });
      }
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Unable to connect to Upwork. Please verify your cookies.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
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
              <KeyRound className="size-5 text-blue-600" />
              Upwork Account Connection
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Manage your connection cookies to fetch live Upwork jobs and client contract histories
            </p>
          </div>
        </div>

        {/* Current Status Pill */}
        <div>
          {isConnected ? (
            <Badge variant="success" className="px-3 py-1 text-xs flex items-center gap-1.5 font-semibold">
              <CheckCircle2 className="size-3.5" />
              <span>Connected ({cookieCount} cookies)</span>
            </Badge>
          ) : (
            <Badge variant="error" className="px-3 py-1 text-xs flex items-center gap-1.5 font-bold">
              <ShieldAlert className="size-3.5" />
              <span>Cookies Needed</span>
            </Badge>
          )}
        </div>
      </div>

      {/* Status Notice Banner */}
      {!isConnected && (
        <div className="p-4 rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-300 flex items-start gap-3">
          <AlertCircle className="size-5 shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
          <div className="space-y-1">
            <h4 className="text-sm font-bold">Upwork Connection Required</h4>
            <p className="text-xs leading-relaxed">
              Without active Upwork cookies, the system cannot load contract histories or client reviews. Follow the 3 quick steps below to connect your session in 30 seconds.
            </p>
          </div>
        </div>
      )}

      {/* Feedback Alert */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center gap-2.5 ${
            feedback.type === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300'
              : 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="size-4 shrink-0 text-red-600" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Step by Step Guide & Paste Box */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Side: Step by Step Guide (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-5">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-50 flex items-center gap-2 mb-3">
              <HelpCircle className="size-4 text-blue-600" />
              How to get your cookies:
            </h3>

            <ol className="space-y-3.5 text-xs text-slate-600 dark:text-slate-400">
              <li className="flex items-start gap-2.5">
                <span className="size-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  1
                </span>
                <span>
                  Open <a href="https://www.upwork.com" target="_blank" rel="noreferrer" className="text-blue-600 font-semibold underline inline-flex items-center gap-0.5">upwork.com <ExternalLink className="size-2.5" /></a> in Chrome or Edge and sign in to your Upwork account.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="size-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  2
                </span>
                <span>
                  Use a browser extension like <strong>Cookie-Editor</strong> and click <strong>Export JSON</strong>.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="size-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  3
                </span>
                <span>
                  Paste the copied JSON text into the box on the right and click <strong>Save & Test Connection</strong>.
                </span>
              </li>
            </ol>

            <div className="mt-5 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-500">
              Your cookies are stored encrypted in your local private environment and are never shared.
            </div>
          </Card>

          {/* Account Card */}
          <Card className="p-5 space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block">
              Active User Account
            </span>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">
              {activeAccount}
            </div>
            <div className="text-xs text-slate-500">
              {cookieCount > 0 ? `${cookieCount} cookies loaded` : 'No cookies saved yet'}
            </div>
          </Card>
        </div>

        {/* Right Side: Paste Box & Controls (7 cols) */}
        <div className="lg:col-span-7">
          <Card className="p-5 flex flex-col justify-between h-full space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Paste Cookie JSON or Header String:
                </label>
                <span className="text-[11px] text-slate-400">JSON format</span>
              </div>

              <textarea
                value={cookieJson}
                onChange={(e) => setCookieJson(e.target.value)}
                rows={isEncryptedCookieFile ? 7 : 10}
                placeholder='[{"name": "oauth2_global_js_token", "value": "..."}, {"name": "XSRF-TOKEN", "value": "..."}]'
                className="w-full p-3 font-mono text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />

              {isEncryptedCookieFile && (
                <div className="mt-3 p-3.5 rounded-lg bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-900 dark:text-blue-200">
                    <KeyRound className="size-4 text-blue-600 shrink-0" />
                    <span>Encrypted Cookie Backup Detected</span>
                  </div>
                  <p className="text-[11px] text-blue-800/80 dark:text-blue-300">
                    Cookie-Editor encrypted this export. Enter the password you chose during export to decrypt:
                  </p>
                  <input
                    type="password"
                    value={decryptPassword}
                    onChange={(e) => setDecryptPassword(e.target.value)}
                    placeholder="Enter decryption password (e.g. Drc@1234)"
                    className="w-full px-3 py-1.5 text-xs rounded-md border border-blue-300 dark:border-blue-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestConnection}
                disabled={isTesting || isSaving}
                className="w-full sm:w-auto text-xs"
              >
                {isTesting ? (
                  <RefreshCw className="size-3.5 me-1.5 animate-spin" />
                ) : (
                  <ShieldCheck className="size-3.5 me-1.5 text-blue-600" />
                )}
                <span>Test Connection Live</span>
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveCookies}
                disabled={isSaving || !cookieJson.trim()}
                className="w-full sm:w-auto text-xs"
              >
                {isSaving ? (
                  <RefreshCw className="size-3.5 me-1.5 animate-spin" />
                ) : (
                  <KeyRound className="size-3.5 me-1.5" />
                )}
                <span>Save & Test Connection</span>
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
