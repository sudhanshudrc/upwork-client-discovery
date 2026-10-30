import * as React from 'react';
import { cn } from '@/components/ui/utils';

export interface CardProps extends React.ComponentProps<'div'> {
  elevated?: boolean;
}

export function Card({ className, elevated = false, ...props }: CardProps) {
  return (
    <div
      data-slot="card"
      className={cn(
        'rounded-xl border border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] text-[#3D4127] dark:text-[#F8F9F3] transition-all duration-150',
        elevated
          ? 'shadow-[var(--shadow-elevated)] border-[#BAC095]'
          : 'shadow-[var(--shadow-card)]',
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn('flex flex-col space-y-1.5 p-5 pb-3', className)}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.ComponentProps<'h3'>) {
  return (
    <h3
      data-slot="card-title"
      className={cn(
        'text-base font-semibold text-[#3D4127] dark:text-[#F8F9F3] tracking-tight leading-snug',
        className
      )}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.ComponentProps<'p'>) {
  return (
    <p
      data-slot="card-description"
      className={cn('text-xs text-[#656C43] dark:text-[#BAC095] leading-normal', className)}
      {...props}
    />
  );
}

export function CardContent({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-content"
      className={cn('p-5 pt-0 text-sm leading-normal', className)}
      {...props}
    />
  );
}

export function CardFooter({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        'flex items-center p-5 pt-0 border-t border-[#F3F7F5] mt-4',
        className
      )}
      {...props}
    />
  );
}

