import { motion } from 'framer-motion';
import {
  Briefcase,
  MapPin,
  Clock,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Star,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { snap } from '@/components/motion/seeds';
import { cn } from '@/components/ui/utils';
import type { FeedJobItem } from '@/services/api';

interface JobFeedTableProps {
  jobs: FeedJobItem[];
  selectedJobUid: string | null;
  onSelectJob: (uid: string) => void;
  onInitialSearch?: () => void;
}

function cleanBudget(raw?: string | null): string | null {
  if (!raw) return null;
  const lower = raw.toLowerCase();
  if (lower.includes('connect_jobtypes') || lower.includes('hourlyrange') || lower.includes('hourly')) {
    const match = raw.match(/\$\d+(?:\.\d+)?(?:\s*-\s*\$\d+(?:\.\d+)?)?/);
    return match ? match[0] : 'Hourly';
  }
  if (lower.includes('fixed')) {
    const match = raw.match(/\$\d+(?:\.\d+)?/);
    return match ? match[0] : 'Fixed';
  }
  return raw;
}

function cleanExperienceLevel(raw?: string | null): string {
  if (!raw) return 'Any Experience';
  const lower = raw.toLowerCase();
  if (lower.includes('intermediate')) return 'Intermediate';
  if (lower.includes('expert')) return 'Expert';
  if (lower.includes('entry')) return 'Entry Level';
  if (raw.includes('_')) {
    const cleaned = raw.replace(/^[0-9a-zA-Z]+_/, '').replace(/_[0-9a-zA-Z]+$/, '');
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }
  return raw;
}

function cleanDuration(raw?: string | null): string | null {
  if (!raw) return null;
  return raw
    .replace(/^est\.\s*time:\s*/i, '')
    .replace(/less than/gi, '<')
    .replace(/more than/gi, '>')
    .replace(/hours?\/week/gi, 'hrs/wk')
    .trim();
}

export function JobFeedTable({
  jobs,
  selectedJobUid,
  onSelectJob,
  onInitialSearch,
}: JobFeedTableProps) {
  if (jobs.length === 0) {
    return (
      <Card className="p-8 text-center space-y-3 border-dashed border-slate-300 dark:border-slate-700">
        <Briefcase className="size-8 mx-auto text-blue-600 dark:text-blue-400" />
        <div className="text-xs text-slate-500">
          No jobs found yet. Click &quot;Search Jobs&quot; above to scan for opportunities.
        </div>
        {onInitialSearch && (
          <Button variant="secondary" size="sm" onClick={onInitialSearch}>
            Search Developer Jobs
          </Button>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-2.5">
      {jobs.map((job) => {
        const isSelected = job.uid === selectedJobUid;
        const location = job.client_location || job.client_location_snippet || job.location;
        const displayBudget = cleanBudget(job.budget);
        const displayExp = cleanExperienceLevel(job.experience_level);
        const displayDuration = cleanDuration(job.duration);

        // Client rating check (when available from Stage 2 or DB enrichment)
        const hasRating = Boolean(
          job.client_rating &&
            job.client_rating.trim() !== '' &&
            parseFloat(job.client_rating) > 0
        );

        // Highlight red ONLY when payment verified is false
        const isRedCard = job.payment_verified === false;

        return (
          <motion.div
            key={job.uid}
            onClick={() => onSelectJob(job.uid)}
            whileHover={snap.hover.whileHover}
            transition={snap.hover.transition}
            className={cn(
              'cursor-pointer rounded-xl border p-3.5 transition-all duration-150 space-y-2 select-none',
              // Highlight red ONLY when payment verified is false
              isRedCard
                ? isSelected
                  ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-950/40 shadow-xs ring-1 ring-rose-400/50'
                  : 'border-rose-200/90 dark:border-rose-900/50 bg-rose-50/20 dark:bg-rose-950/20 hover:border-rose-300 dark:hover:border-rose-800'
                : isSelected
                  ? 'border-blue-600 bg-blue-50/70 dark:bg-blue-950/40 shadow-xs'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
            )}
          >
            {/* Top Status Bar: Posted Time, Payment Verified, Risk Warning */}
            <div className="flex items-center justify-between gap-1.5 text-[10px]">
              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                {job.posted_time && (
                  <span className="flex items-center gap-1 font-medium">
                    <Clock className="size-2.5 text-slate-400" />
                    {job.posted_time}
                  </span>
                )}

                {job.payment_verified ? (
                  <span className="inline-flex items-center gap-0.5 text-emerald-700 dark:text-emerald-400 font-medium">
                    <CheckCircle2 className="size-2.5 text-emerald-600 dark:text-emerald-400" />
                    Verified
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-0.5 text-rose-600 dark:text-rose-400 font-medium">
                    <AlertCircle className="size-2.5 text-rose-500" />
                    Unverified
                  </span>
                )}
              </div>

              {/* Warning Indicator only for Unverified Payment */}
              {isRedCard && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold text-rose-700 dark:text-rose-400 bg-rose-100/70 dark:bg-rose-950/70 border border-rose-200 dark:border-rose-900/50">
                  <AlertCircle className="size-2.5 text-rose-600 dark:text-rose-400" />
                  Payment Unverified
                </span>
              )}
            </div>

            {/* Title & Budget */}
            <div className="flex justify-between items-start gap-2">
              <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-50 line-clamp-2 leading-snug">
                {job.title}
              </h4>
              {displayBudget && (
                <Badge variant="neutral" className="text-[10px] shrink-0 font-mono">
                  {displayBudget}
                </Badge>
              )}
            </div>

            {/* Duration / Commitment */}
            {displayDuration && (
              <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                <Calendar className="size-3 shrink-0 text-slate-400" />
                <span className="truncate">{displayDuration}</span>
              </div>
            )}

            {/* Bottom Row: Location, Client Rating, Experience Level */}
            <div className="pt-1 flex items-center justify-between text-[11px] border-t border-slate-100 dark:border-slate-800/80">
              {/* Location & Spend */}
              <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400 truncate max-w-[170px]">
                {location ? (
                  <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400 font-medium truncate">
                    <MapPin className="size-3 shrink-0" />
                    <span className="truncate">{location}</span>
                  </span>
                ) : (
                  <span className="text-slate-400 text-[10px]">Location unlisted</span>
                )}

                {job.client_spent ? (
                  <span className="text-slate-400 text-[10px] truncate">
                    • {job.client_spent}
                  </span>
                ) : (
                  <span className="text-slate-400 text-[10px] truncate">
                    • $0 spent
                  </span>
                )}
              </div>

              {/* Client Rating (if present) & Experience Level */}
              <div className="flex items-center gap-2 shrink-0">
                {hasRating ? (
                  <span className="inline-flex items-center gap-1 font-semibold text-[11px] text-amber-700 dark:text-amber-400 font-mono">
                    <Star className="size-3 text-amber-500 fill-amber-500" />
                    {job.client_rating}
                  </span>
                ) : null}

                <span className="text-slate-400 text-[10px]">{displayExp}</span>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
