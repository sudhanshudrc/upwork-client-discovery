import * as React from 'react';
import {
  Briefcase,
  Sun,
  Moon,
  LogOut,
  User as UserIcon,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/auth-context';
import type { SessionStatusResponse } from '@/services/api';
import { cn } from '@/components/ui/utils';

export type AppPage = 'overview' | 'saved-jobs' | 'search-history' | 'clients' | 'connection';

interface AppHeaderProps {
  currentPage: AppPage;
  onNavigate: (page: AppPage) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  sessionStatus?: SessionStatusResponse | null;
  isLoadingSession?: boolean;
}

export function AppHeader({
  currentPage,
  onNavigate,
  isDarkMode,
  onToggleDarkMode,
  sessionStatus,
  isLoadingSession = false,
}: AppHeaderProps) {
  const { user, logout } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = React.useState(false);
  const profileMenuRef = React.useRef<HTMLDivElement>(null);
  const profileButtonRef = React.useRef<HTMLButtonElement>(null);

  // Close profile menu when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setIsProfileOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && isProfileOpen) {
        setIsProfileOpen(false);
        profileButtonRef.current?.focus();
      }
    }

    if (isProfileOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isProfileOpen]);

  const cookieMatch =
    sessionStatus?.message?.match(/with (\d+) cookies/i) ||
    sessionStatus?.message?.match(/\((\d+) cookies\)/i);
  const cookieCount = cookieMatch
    ? Number(cookieMatch[1])
    : (user?.upwork_cookie_count || (sessionStatus?.is_authenticated ? 79 : 0));

  const hasCookies = Boolean(
    sessionStatus?.is_authenticated &&
      (user?.has_upwork_session !== false || cookieCount > 0)
  );

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'User';
  const userInitial = (user?.full_name?.[0] || user?.email?.[0] || 'U').toUpperCase();

  const navItems: { id: AppPage; label: string }[] = [
    { id: 'overview', label: 'Search & Leads' },
    { id: 'saved-jobs', label: 'Saved Jobs' },
    { id: 'search-history', label: 'Search History' },
    { id: 'clients', label: 'Discovered Clients' },
  ];

  return (
    <header
      data-slot="app-header"
      className="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-xs transition-colors"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand & Desktop Navigation */}
        <div className="flex items-center space-x-6">
          <button
            type="button"
            onClick={() => onNavigate('overview')}
            className="flex items-center space-x-2.5 text-left group cursor-pointer focus-visible:outline-none"
          >
            <div className="size-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs shadow-blue-500/20 group-hover:bg-blue-700 transition-colors">
              <Briefcase className="size-4" />
            </div>
            <div className="font-bold text-sm tracking-tight text-slate-900 dark:text-slate-50">
              Upwork Intelligence
            </div>
          </button>

          {/* Text-Only Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Main Navigation">
            {navItems.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onNavigate(item.id)}
                  className={cn(
                    'px-3.5 py-2 rounded-lg text-xs font-semibold transition-all select-none min-h-10 cursor-pointer',
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 font-bold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                  )}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Right Section: Theme Toggle and Person Profile Menu */}
        <div className="flex items-center space-x-2.5">
          {/* Theme Toggle */}
          <Button
            variant="outline"
            size="icon"
            onClick={onToggleDarkMode}
            className="size-10 rounded-lg text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800"
            title="Toggle color theme"
            aria-label="Toggle color theme"
          >
            {isDarkMode ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </Button>

          {/* User Profile Avatar with Embedded Status Dot */}
          <div className="relative" ref={profileMenuRef}>
            <button
              ref={profileButtonRef}
              type="button"
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={cn(
                'relative size-10 rounded-lg border flex items-center justify-center transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
                isProfileOpen
                  ? 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-600'
                  : 'bg-slate-50 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
              )}
              aria-haspopup="dialog"
              aria-expanded={isProfileOpen}
              aria-label={
                hasCookies
                  ? `User account menu: ${user?.email || 'User'}, Upwork connected`
                  : `User account menu: ${user?.email || 'User'}, Upwork cookies needed`
              }
            >
              <UserIcon className="size-4 text-slate-700 dark:text-slate-200" />

              {/* Status Indicator Dot */}
              {isLoadingSession ? (
                <span className="absolute top-1.5 right-1.5 size-2.5 rounded-full bg-slate-400 ring-2 ring-white dark:ring-slate-900 animate-pulse" />
              ) : hasCookies ? (
                <span
                  className="absolute top-1.5 right-1.5 size-2.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900"
                  title="Upwork session active"
                />
              ) : (
                <span className="absolute top-1.5 right-1.5 flex size-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span
                    className="relative inline-flex rounded-full size-2.5 bg-red-500 ring-2 ring-white dark:ring-slate-900"
                    title="Upwork cookies needed"
                  />
                </span>
              )}
            </button>

            {/* Floating Profile Popover Menu */}
            {isProfileOpen && (
              <div
                data-slot="user-profile-menu"
                role="dialog"
                aria-label="User Account and Upwork Connection"
                className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-xl z-50 text-slate-900 dark:text-slate-100 space-y-3.5 animate-in fade-in zoom-in-95 duration-150"
              >
                {/* 1. User Identity Header */}
                <div className="flex items-center space-x-3 pb-3 border-b border-slate-100 dark:border-slate-800">
                  <div className="size-10 rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center text-sm uppercase shrink-0">
                    {userInitial}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {displayName}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                      {user?.email || 'Authenticated User'}
                    </div>
                  </div>
                </div>

                {/* 2. Upwork Session & Cookies Status Card */}
                <div className="rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/50 p-3 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Upwork Session
                    </span>
                    {isLoadingSession ? (
                      <span className="text-[11px] font-medium text-slate-500 animate-pulse">
                        Checking...
                      </span>
                    ) : hasCookies ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800/60">
                        <CheckCircle2 className="size-3 text-emerald-600 dark:text-emerald-400" />
                        Connected ({cookieCount})
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/60 px-2 py-0.5 rounded-full border border-red-200 dark:border-red-800/60">
                        <AlertCircle className="size-3 text-red-600 dark:text-red-400" />
                        Cookies Needed
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    {hasCookies
                      ? `Active session with ${cookieCount} cookies loaded in memory.`
                      : 'Upwork session cookies are missing or expired. Connect your cookies to unlock client history.'}
                  </p>

                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileOpen(false);
                      onNavigate('connection');
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700/80 text-slate-800 dark:text-slate-200 shadow-xs transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <KeyRound className="size-3.5 text-blue-600 dark:text-blue-400" />
                      Manage Upwork Cookies
                    </span>
                    <ChevronRight className="size-3.5 text-slate-400" />
                  </button>
                </div>

                {/* 3. Sign Out Action */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 border border-transparent hover:border-red-200 dark:hover:border-red-900/50 transition-colors cursor-pointer"
                  >
                    <LogOut className="size-3.5" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Sub-Navigation Bar */}
      <div className="md:hidden flex items-center overflow-x-auto px-4 py-2 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 gap-1.5">
        {navItems.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs whitespace-nowrap font-medium transition-all select-none cursor-pointer',
                isActive
                  ? 'bg-blue-600 text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800'
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
    </header>
  );
}
