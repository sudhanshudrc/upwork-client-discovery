import * as React from 'react';
import { cn } from '@/components/ui/utils';

export interface InputProps extends React.ComponentProps<'input'> {}

export function Input({ className, type = 'text', ...props }: InputProps) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'flex h-11 w-full rounded-lg border border-[#BAC095] dark:border-[#4A5129] bg-white dark:bg-[#15180E] px-3.5 py-2 text-sm text-[#3D4127] dark:text-[#F8F9F3] placeholder:text-[#656C43]/60 dark:placeholder:text-[#BAC095]/60 transition-colors outline-none focus-visible:border-[#636B2F] focus-visible:ring-2 focus-visible:ring-[#636B2F]/20 disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  );
}

