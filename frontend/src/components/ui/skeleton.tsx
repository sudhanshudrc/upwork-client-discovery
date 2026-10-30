import * as React from 'react';
import { cn } from '@/components/ui/utils';

export interface SkeletonProps extends React.ComponentProps<'div'> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        'animate-pulse rounded-md bg-[#EAF0EC] transition-colors',
        className
      )}
      {...props}
    />
  );
}

