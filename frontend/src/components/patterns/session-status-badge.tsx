import { ShieldCheck, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { SessionStatusResponse } from '@/services/api';

interface SessionStatusBadgeProps {
  status?: SessionStatusResponse | null;
  isLoading?: boolean;
}

export function SessionStatusBadge({ status, isLoading = false }: SessionStatusBadgeProps) {
  if (isLoading) {
    return (
      <Badge variant="neutral" className="animate-pulse">
        Checking connection...
      </Badge>
    );
  }

  if (!status || !status.is_authenticated) {
    return (
      <Badge variant="warning">
        <AlertCircle className="size-3 me-1" />
        Upwork Disconnected
      </Badge>
    );
  }

  const cleanMessage = status.message?.match(/with (\d+) cookies/i)
    ? `Upwork Connected (${status.message.match(/with (\d+) cookies/i)?.[1]} cookies)`
    : status.message || 'Upwork Connected';

  return (
    <Badge
      variant={status.rate_limit_health === 'GREEN' ? 'brand' : 'warning'}
      className="hidden sm:inline-flex"
    >
      <ShieldCheck className="size-3 me-1" />
      {cleanMessage}
    </Badge>
  );
}
