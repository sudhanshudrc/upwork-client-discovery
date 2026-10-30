import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/components/ui/utils';

export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(
        'inline-flex h-11 items-center justify-center rounded-lg bg-[#EFF2E3] dark:bg-[#15180E] p-1 text-[#656C43] dark:text-[#BAC095] border border-[#E1E4D3] dark:border-[#2E331E]',
        className
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3.5 py-1.5 text-xs font-medium transition-all outline-none disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-white dark:data-[state=active]:bg-[#2B3118] data-[state=active]:text-[#3D4127] dark:data-[state=active]:text-[#D4DE95] data-[state=active]:shadow-sm data-[state=active]:font-semibold',
        className
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn(
        'mt-3 outline-none focus-visible:ring-2 focus-visible:ring-[#636B2F]',
        className
      )}
      {...props}
    />
  );
}

