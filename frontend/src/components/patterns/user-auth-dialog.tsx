import * as React from 'react';
import { LogIn, UserPlus, Mail, Lock, User, RefreshCw, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { useAuth } from '@/context/auth-context';

interface UserAuthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultMode?: 'login' | 'register';
}

export function UserAuthDialog({
  open,
  onOpenChange,
  defaultMode = 'login',
}: UserAuthDialogProps) {
  const { login, register } = useAuth();
  const [mode, setMode] = React.useState<'login' | 'register'>(defaultMode);
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [fullName, setFullName] = React.useState('');
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setMode(defaultMode);
      setError(null);
      setPassword('');
    }
  }, [open, defaultMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError('Please provide a valid email address.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }
    if (mode === 'register' && password.length < 8) {
      setError('Password must be at least 8 characters in length.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login(cleanEmail, password);
      } else {
        await register(cleanEmail, password, fullName.trim() || undefined);
      }
      onOpenChange(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {mode === 'login' ? (
              <LogIn className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
            ) : (
              <UserPlus className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
            )}
            <DialogTitle>
              {mode === 'login' ? 'Sign In to Your Workspace' : 'Create Tenant Account'}
            </DialogTitle>
          </div>
          <DialogDescription>
            {mode === 'login'
              ? 'Access your private profile, isolated Upwork cookie vault, and client discovery intelligence.'
              : 'Create an isolated workspace account to store your private session cookies and run pipelines.'}
          </DialogDescription>
        </DialogHeader>

        {/* Tab Switcher */}
        <div className="flex border-b border-[#E1E4D3] dark:border-[#2E331E] mb-2">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setError(null);
            }}
            className={`flex-1 pb-2 text-xs font-semibold text-center transition-colors border-b-2 ${
              mode === 'login'
                ? 'border-[#636B2F] text-[#636B2F] dark:border-[#D4DE95] dark:text-[#D4DE95]'
                : 'border-transparent text-[#656C43] dark:text-[#BAC095] hover:text-[#3D4127]'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('register');
              setError(null);
            }}
            className={`flex-1 pb-2 text-xs font-semibold text-center transition-colors border-b-2 ${
              mode === 'register'
                ? 'border-[#636B2F] text-[#636B2F] dark:border-[#D4DE95] dark:text-[#D4DE95]'
                : 'border-transparent text-[#656C43] dark:text-[#BAC095] hover:text-[#3D4127]'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-lg border border-[#B91C1C]/30 bg-[#FDF2F2] dark:bg-[#3D1414] p-3 text-xs text-[#B91C1C] dark:text-[#F87171] flex items-start gap-2">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 py-1">
          {mode === 'register' && (
            <div className="space-y-1">
              <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
                Full Name / Agency (Optional)
              </label>
              <div className="relative">
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Alex Johnson or Dev Agency"
                  className="pe-8"
                />
                <User className="size-3.5 text-[#656C43] dark:text-[#BAC095] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Email Address
            </label>
            <div className="relative">
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="pe-8"
              />
              <Mail className="size-3.5 text-[#656C43] dark:text-[#BAC095] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-[#4D5333] dark:text-[#DCE1C4]">
              Password
            </label>
            <div className="relative">
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === 'register' ? 'Minimum 8 characters' : 'Enter password'}
                className="pe-8"
              />
              <Lock className="size-3.5 text-[#656C43] dark:text-[#BAC095] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              className="w-full text-xs h-9"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <RefreshCw className="size-3.5 me-1.5 animate-spin" />
              ) : mode === 'login' ? (
                <LogIn className="size-3.5 me-1.5" />
              ) : (
                <UserPlus className="size-3.5 me-1.5" />
              )}
              {mode === 'login' ? 'Sign In' : 'Register Account'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

