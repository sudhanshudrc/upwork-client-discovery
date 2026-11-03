import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/components/ui/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium tracking-wide transition-colors select-none',
  {
    variants: {
      variant: {
        'tier-a':
          'bg-blue-50 text-blue-700 border border-blue-200 font-semibold dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
        'tier-b':
          'bg-slate-50 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
        'tier-c':
          'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800/50 dark:text-slate-400 dark:border-slate-700',
        brand:
          'bg-blue-50 text-blue-700 border border-blue-200 font-medium dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
        neutral:
          'bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
        success:
          'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800',
        warning:
          'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
        error:
          'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  }
);

export interface BadgeProps
  extends React.ComponentProps<'span'>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}
