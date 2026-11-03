import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase,
  Lock,
  Mail,
  User,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Loader2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/context/auth-context';

export function AuthPage() {
  const [tab, setTab] = React.useState<'login' | 'register'>('login');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [fullName, setFullName] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const { login, register } = useAuth();

  const handleTabChange = (newTab: 'login' | 'register') => {
    setTab(newTab);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !password.trim()) {
      setErrorMessage('Please enter both your email and password.');
      return;
    }

    if (tab === 'register' && password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (tab === 'login') {
        await login(cleanEmail, password);
        setSuccessMessage('Signed in successfully! Loading your workspace...');
      } else {
        await register(cleanEmail, password, fullName.trim() || undefined);
        setSuccessMessage('Account created successfully! Loading your workspace...');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed';
      setErrorMessage(msg);
      setIsSubmitting(false);
    }
  };

  const isAccountExistsError = Boolean(
    errorMessage && errorMessage.toLowerCase().includes('already exists')
  );

  const isInvalidCredentialsError = Boolean(
    errorMessage && errorMessage.toLowerCase().includes('invalid email or password')
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center items-center px-4 py-12 transition-colors">
      <div className="w-full max-w-md space-y-6">
        {/* App Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex size-12 rounded-xl bg-blue-600 text-white items-center justify-center shadow-md shadow-blue-500/20">
            <Briefcase className="size-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Lead Intelligence
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Client Discovery and Decision-Maker Platform
          </p>
        </div>

        {/* Auth Card */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-lg">
          {/* Tab Selector */}
          <div className="grid grid-cols-2 p-1 m-4 mb-2 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => handleTabChange('login')}
              className={`py-2 text-xs font-semibold rounded-md transition-all ${
                tab === 'login'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-50 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleTabChange('register')}
              className={`py-2 text-xs font-semibold rounded-md transition-all ${
                tab === 'register'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-50 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
              }`}
            >
              Create Account
            </button>
          </div>

          <CardContent className="pt-2">
            {/* Success Confirmation Banner */}
            {successMessage && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-200 flex items-center gap-2 font-medium"
              >
                <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span>{successMessage}</span>
              </motion.div>
            )}

            {/* Error Message Alert */}
            {errorMessage && !successMessage && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-300 space-y-2"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  <span className="leading-snug">{errorMessage}</span>
                </div>

                {/* Helpful shortcut if email already exists during registration */}
                {isAccountExistsError && tab === 'register' && (
                  <button
                    type="button"
                    onClick={() => handleTabChange('login')}
                    className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:underline pt-1"
                  >
                    <span>Click here to Sign In with this email</span>
                    <ArrowRight className="size-3" />
                  </button>
                )}

                {/* Helpful shortcut if login failed with invalid credentials */}
                {isInvalidCredentialsError && tab === 'login' && (
                  <button
                    type="button"
                    onClick={() => handleTabChange('register')}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline pt-1"
                  >
                    <span>Need an account? Click here to register</span>
                    <ArrowRight className="size-3" />
                  </button>
                )}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <AnimatePresence mode="wait">
                {tab === 'register' && (
                  <motion.div
                    key="name-field"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-1.5"
                  >
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Full Name (Optional)
                    </label>
                    <div className="relative">
                      <User className="size-4 absolute left-3 top-3 text-slate-400" />
                      <Input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="John Doe"
                        className="pl-9"
                        disabled={isSubmitting}
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="size-4 absolute left-3 top-3 text-slate-400" />
                  <Input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="pl-9"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Password
                  </label>
                  {tab === 'register' && (
                    <span className="text-[11px] text-slate-400">At least 8 characters</span>
                  )}
                </div>
                <div className="relative">
                  <Lock className="size-4 absolute left-3 top-3 text-slate-400" />
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={tab === 'register' ? 8 : 1}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="pl-9 pr-9"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 mt-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : tab === 'login' ? (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="size-4" />
                  </>
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight className="size-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer info */}
        <p className="text-center text-xs text-slate-400 dark:text-slate-500">
          Secure Upwork automation & lead prospecting workspace.
        </p>
      </div>
    </div>
  );
}
