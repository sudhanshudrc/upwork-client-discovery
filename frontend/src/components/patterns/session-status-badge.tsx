import { ShieldCheck, AlertCircle, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { SessionStatusResponse } from '@/services/api';

interface SessionStatusBadgeProps {
  status?: SessionStatusResponse | null;
  isLoading?: boolean;
  profileName?: string;
  onOpenSettings?: () => void;
}

export function SessionStatusBadge({
  status,
  isLoading = false,
  profileName = 'default',
  onOpenSettings,
}: SessionStatusBadgeProps) {
  if (isLoading) {
    return (
      <Badge variant="neutral" className="animate-pulse flex items-center gap-1">
        <User className="size-3" />
        <span>{profileName}: Checking...</span>
      </Badge>
    );
  }

  if (!status || !status.is_authenticated) {
    return (
      <button
        type="button"
        onClick={onOpenSettings}
        className="cursor-pointer transition-opacity hover:opacity-85 text-left"
        title="Session not connected. Click to import cookies or switch profile."
      >
        <Badge variant="warning" className="flex items-center gap-1">
          <AlertCircle className="size-3" />
          <span>Profile [{profileName}]: Disconnected</span>
        </Badge>
      </button>
    );
  }

  const cookieMatch =
    status.message?.match(/with (\d+) cookies/i) ||
    status.message?.match(/\((\d+) cookies\)/i);
  const cookieCount = cookieMatch ? cookieMatch[1] : null;
  const label = cookieCount
    ? `Profile [${profileName}]: ${cookieCount} cookies`
    : `Profile [${profileName}]: Connected`;

  return (
    <button
      type="button"
      onClick={onOpenSettings}
      className="cursor-pointer transition-opacity hover:opacity-85 text-left"
      title={`Active session for profile '${profileName}'. Click to test connection or manage cookies.`}
    >
      <Badge
        variant={status.rate_limit_health === 'GREEN' ? 'brand' : 'warning'}
        className="hidden sm:inline-flex items-center gap-1"
      >
        <ShieldCheck className="size-3" />
        <span>{label}</span>
      </Badge>
    </button>
  );
}
