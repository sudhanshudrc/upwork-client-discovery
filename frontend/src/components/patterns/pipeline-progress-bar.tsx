import { CheckCircle2, Clock, PlayCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';

export interface PipelineStage {
  id: number;
  name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'ERROR';
  description: string;
}

interface PipelineProgressBarProps {
  currentStageId?: number;
  stages?: PipelineStage[];
  isRunning?: boolean;
}

const DEFAULT_STAGES: PipelineStage[] = [
  { id: 1, name: 'Job Discovery', status: 'COMPLETED', description: 'Matched relevant client postings' },
  { id: 2, name: 'Client History', status: 'COMPLETED', description: 'Loaded past hiring feedback' },
  { id: 3, name: 'Client Identity', status: 'COMPLETED', description: 'Found decision-maker name & company' },
  { id: 4, name: 'Lead Matching', status: 'COMPLETED', description: 'Matched against LinkedIn profiles' },
  { id: 5, name: 'Ready to Outreach', status: 'COMPLETED', description: 'Verified leads ready for export' },
];

export function PipelineProgressBar({
  stages = DEFAULT_STAGES,
  isRunning = false,
}: PipelineProgressBarProps) {
  return (
    <Card className="p-4 border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414]">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#EFF2E3] dark:border-[#2E331E]">
        <div className="flex items-center gap-2">
          <PlayCircle className="size-4 text-[#636B2F] dark:text-[#D4DE95]" />
          <span className="text-xs font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
            Lead Discovery Flow
          </span>
        </div>
        {isRunning && (
          <span className="text-[11px] text-[#636B2F] dark:text-[#D4DE95] font-mono animate-pulse">
            Processing steps...
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
        {stages.map((stage) => {
          const isDone = stage.status === 'COMPLETED';
          return (
            <div
              key={stage.id}
              className={`p-2.5 rounded-lg border text-xs transition-all ${
                isDone
                  ? 'border-[#636B2F]/40 bg-[#EFF4DC]/50 dark:bg-[#2B3118]/30'
                  : 'border-[#BAC095] dark:border-[#2E331E] bg-[#EFF2E3] dark:bg-[#15180E]'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-[11px] text-[#3D4127] dark:text-[#F8F9F3]">
                  Step {stage.id}
                </span>
                {isDone ? (
                  <CheckCircle2 className="size-3 text-[#636B2F] dark:text-[#D4DE95]" />
                ) : (
                  <Clock className="size-3 text-[#656C43] dark:text-[#BAC095]" />
                )}
              </div>
              <div className="font-medium text-[#636B2F] dark:text-[#D4DE95] text-[11px] truncate">
                {stage.name}
              </div>
              <div className="text-[10px] text-[#656C43] dark:text-[#BAC095] truncate mt-0.5">
                {stage.description}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
