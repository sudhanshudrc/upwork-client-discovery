import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/components/ui/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium tracking-wide transition-colors select-none',
  {
    variants: {
      variant: {
        'tier-a':
          'bg-[#EFF4DC] text-[#3D4127] border border-[#636B2F] font-semibold dark:bg-[#2B3118] dark:text-[#D4DE95]',
        'tier-b':
          'bg-[#F4F6EA] text-[#3D4127] border border-[#BAC095] dark:bg-[#222714] dark:text-[#DCE1C4]',
        'tier-c':
          'bg-[#F8F9F3] text-[#656C43] border border-[#D8DCC5] dark:bg-[#1B1E10] dark:text-[#BAC095]',
        brand:
          'bg-[#EFF4DC] text-[#636B2F] border border-[#636B2F] font-medium dark:bg-[#2B3118] dark:text-[#D4DE95]',
        neutral:
          'bg-[#EFF2E3] text-[#4D5333] border border-[#E1E4D3] dark:bg-[#15180E] dark:text-[#DCE1C4] dark:border-[#2E331E]',
        success:
          'bg-[#EFF4DC] text-[#636B2F] border border-[#636B2F] dark:bg-[#2B3118] dark:text-[#D4DE95]',
        warning:
          'bg-[#FEF6EC] text-[#B37D2C] border border-[#F2D7B3] dark:bg-[#2A1D0B] dark:text-[#E9B86A] dark:border-[#5C3E14]',
        error:
          'bg-[#FDF2F2] text-[#B91C1C] border border-[#F3C4C4] dark:bg-[#3D1414] dark:text-[#F87171] dark:border-[#7F1D1D]',
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

