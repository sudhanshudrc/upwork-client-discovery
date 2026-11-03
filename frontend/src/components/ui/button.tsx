import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/components/ui/utils';
import { spring } from '@/components/motion/seeds';

const buttonVariants = cva(
  'inline-flex items-center justify-center font-medium text-sm transition-colors duration-150 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none min-h-10',
  {
    variants: {
      variant: {
        primary:
          'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-sm dark:bg-blue-600 dark:hover:bg-blue-500 dark:text-white',
        secondary:
          'bg-slate-100 text-slate-800 border border-slate-200 hover:bg-slate-200 hover:border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700 dark:hover:bg-slate-700',
        outline:
          'bg-transparent border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white hover:border-slate-300',
        ghost:
          'bg-transparent text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white',
        danger:
          'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-sm',
      },
      size: {
        sm: 'h-8 px-3 text-xs min-w-[32px]',
        md: 'h-10 px-4 text-sm min-w-10',
        lg: 'h-11 px-5 text-base min-w-11',
        icon: 'size-10 p-0',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends Omit<HTMLMotionProps<'button'>, 'ref'>,
    VariantProps<typeof buttonVariants> {
  disableMotion?: boolean;
}

export function Button({
  className,
  variant,
  size,
  disableMotion = false,
  children,
  ...props
}: ButtonProps) {
  const motionProps = disableMotion ? {} : spring.press;

  return (
    <motion.button
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      whileTap={motionProps.whileTap}
      transition={motionProps.transition}
      {...props}
    >
      {children}
    </motion.button>
  );
}
