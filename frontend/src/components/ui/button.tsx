import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/components/ui/utils';
import { spring } from '@/components/motion/seeds';

const buttonVariants = cva(
  'inline-flex items-center justify-center font-medium text-sm transition-colors duration-150 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-[#636B2F] focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none min-h-11',
  {
    variants: {
      variant: {
        primary:
          'bg-[#636B2F] text-[#F8F9F3] hover:bg-[#505724] active:bg-[#3D4127] shadow-sm dark:bg-[#D4DE95] dark:text-[#15180E] dark:hover:bg-[#E4EBB2]',
        secondary:
          'bg-[#EFF2E3] text-[#3D4127] border border-[#BAC095] hover:bg-[#E7EBD6] hover:border-[#636B2F] dark:bg-[#202414] dark:text-[#F8F9F3] dark:border-[#4A5129]',
        outline:
          'bg-transparent border border-[#BAC095] dark:border-[#4A5129] text-[#4D5333] dark:text-[#DCE1C4] hover:bg-[#EFF2E3] dark:hover:bg-[#292E1B] hover:text-[#3D4127] dark:hover:text-[#F8F9F3] hover:border-[#636B2F]',
        ghost:
          'bg-transparent text-[#4D5333] dark:text-[#DCE1C4] hover:bg-[#EFF2E3] dark:hover:bg-[#292E1B] hover:text-[#3D4127] dark:hover:text-[#F8F9F3]',
        danger:
          'bg-[#B91C1C] text-[#FBFCFC] hover:bg-[#991B1B] shadow-sm',
      },
      size: {
        sm: 'h-9 px-3 text-xs min-w-[36px]',
        md: 'h-11 px-4 text-sm min-w-11',
        lg: 'h-12 px-6 text-base min-w-12',
        icon: 'size-11 p-0',
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
