import { motion } from 'framer-motion';
import { Briefcase, MapPin } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { snap } from '@/components/motion/seeds';
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

export function JobFeedTable({
  jobs,
  selectedJobUid,
  onSelectJob,
  onInitialSearch,
}: JobFeedTableProps) {
  if (jobs.length === 0) {
    return (
      <Card className="p-8 text-center space-y-3 border-dashed border-[#BAC095]">
        <Briefcase className="size-8 mx-auto text-[#636B2F] dark:text-[#D4DE95]" />
        <div className="text-xs text-[#656C43] dark:text-[#BAC095]">
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

        return (
          <motion.div
            key={job.uid}
            onClick={() => onSelectJob(job.uid)}
            whileHover={snap.hover.whileHover}
            transition={snap.hover.transition}
            className={`cursor-pointer rounded-xl border p-4 transition-all duration-150 ${
              isSelected
                ? 'border-[#636B2F] bg-[#EFF4DC] dark:bg-[#2B3118]/60 shadow-sm'
                : 'border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] hover:border-[#BAC095]'
            }`}
          >
            <div className="flex justify-between items-start gap-2">
              <h4 className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3] line-clamp-2 leading-snug">
                {job.title}
              </h4>
              {displayBudget && (
                <Badge variant="neutral" className="text-[10px] shrink-0 font-mono">
                  {displayBudget}
                </Badge>
              )}
            </div>

            {/* Prominent Client Location */}
            {location && (
              <div className="flex items-center gap-1 text-[11px] text-[#636B2F] dark:text-[#D4DE95] font-medium mt-1.5">
                <MapPin className="size-3 shrink-0 text-[#636B2F] dark:text-[#D4DE95]" />
                <span className="truncate">{location}</span>
              </div>
            )}

            {job.snippet && (
              <p className="text-[11px] text-[#656C43] dark:text-[#BAC095] line-clamp-2 mt-1.5 leading-relaxed">
                {job.snippet}
              </p>
            )}

            <div className="flex items-center justify-between text-[11px] text-[#656C43] dark:text-[#BAC095] mt-2.5 pt-2 border-t border-[#EFF2E3] dark:border-[#2E331E]">
              <span className="font-mono text-[10px]">ID: {job.uid.slice(-6)}</span>
              <span>{displayExp}</span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
