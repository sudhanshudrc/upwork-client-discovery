import * as React from 'react';
import { cn } from '@/components/ui/utils';

export interface ProgressProps extends React.ComponentProps<'div'> {
  value?: number;
  max?: number;
  indicatorColor?: string;
}

export function Progress({
  className,
  value = 0,
  max = 100,
  indicatorColor = 'bg-[#14746F]',
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div
      data-slot="progress"
      className={cn(
        'relative h-2 w-full overflow-hidden rounded-full bg-[#EAF0EC]',
        className
      )}
      {...props}
    >
      <div
        className={cn('h-full transition-all duration-300 ease-out', indicatorColor)}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export interface FactorScoreProps {
  label: string;
  weight: string;
  score: number;
  colorClass?: string;
  className?: string;
}

export function FactorScoreBar({
  label,
  weight,
  score,
  colorClass = 'bg-[#14746F]',
  className,
}: FactorScoreProps) {
  return (
    <div className={cn('flex flex-col space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[#2C5756] font-medium">
          {label} <span className="text-[#5A7E7B] text-[10px]">({weight})</span>
        </span>
        <span className="font-mono font-semibold text-[#0F3D3E]">
          {score.toFixed(1)}%
        </span>
      </div>
      <Progress value={score} indicatorColor={colorClass} className="h-1.5" />
    </div>
  );
}

