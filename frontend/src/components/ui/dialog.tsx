import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/components/ui/utils';

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogPortal = DialogPrimitive.Portal;
export const DialogClose = DialogPrimitive.Close;

export function DialogOverlay({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      data-slot="dialog-overlay"
      className={cn(
        'fixed inset-0 z-[100] bg-[#15180E]/70 backdrop-blur-sm transition-opacity duration-150',
        className
      )}
      {...props}
    />
  );
}

export interface DialogContentProps
  extends React.ComponentProps<typeof DialogPrimitive.Content> {
  showCloseButton?: boolean;
}

export function DialogContent({
  className,
  children,
  showCloseButton = true,
  ...props
}: DialogContentProps) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-y-auto pointer-events-none">
        <DialogPrimitive.Content asChild {...props}>
          <motion.div
            data-slot="dialog-content"
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              'pointer-events-auto relative w-full max-w-lg rounded-xl border border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] p-6 text-[#3D4127] dark:text-[#F8F9F3] shadow-[var(--shadow-modal)] outline-none my-auto max-h-[90vh] overflow-y-auto',
              className
            )}
          >
            {children}
            {showCloseButton && (
              <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1.5 text-[#656C43] dark:text-[#BAC095] transition-colors hover:bg-[#EFF2E3] dark:hover:bg-[#15180E] hover:text-[#3D4127] dark:hover:text-[#F8F9F3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#636B2F]">
                <X className="size-4" />
                <span className="sr-only">Close</span>
              </DialogPrimitive.Close>
            )}
          </motion.div>
        </DialogPrimitive.Content>
      </div>
    </DialogPortal>
  );
}

export function DialogHeader({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="dialog-header"
      className={cn('flex flex-col space-y-1.5 pb-4 border-b border-[#EFF2E3] dark:border-[#2E331E]', className)}
      {...props}
    />
  );
}

export function DialogFooter({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        'flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4 border-t border-[#EFF2E3] dark:border-[#2E331E] mt-6',
        className
      )}
      {...props}
    />
  );
}

export function DialogTitle({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn('text-lg font-semibold tracking-tight text-[#0F3D3E]', className)}
      {...props}
    />
  );
}

export function DialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn('text-xs text-[#5A7E7B] leading-relaxed', className)}
      {...props}
    />
  );
}
