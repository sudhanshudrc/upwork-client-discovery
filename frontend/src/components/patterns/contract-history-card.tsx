import { Layers } from 'lucide-react';
import type { ContractRecord } from '@/services/api';

interface ContractHistoryCardProps {
  contracts?: ContractRecord[];
}

export function ContractHistoryCard({ contracts = [] }: ContractHistoryCardProps) {
  if (contracts.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-300 dark:border-slate-700 rounded-lg space-y-2">
        <div className="font-semibold text-slate-800 dark:text-slate-200">
          No contract history loaded yet
        </div>
        <p className="text-[11px] text-slate-500 max-w-md mx-auto leading-relaxed">
          Upwork masks client names on jobs by default. Past freelancer reviews frequently mention client names directly. Click &quot;Fetch History&quot; above to load past feedback.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-600">
        <Layers className="size-3.5" />
        Client Past Contract Reviews ({contracts.length})
      </div>

      {contracts.map((contract, idx) => {
        const title = contract.past_title || contract.contract_title || `Contract #${contract.contract_index || idx + 1}`;
        const price = contract.date_and_budget || contract.rate_or_price;
        const reviewClean = contract.freelancer_review_clean || contract.freelancer_feedback;
        const reviewExcluded = contract.excluded_client_praise || contract.client_feedback;
        const minedName = contract.client_name_mined;

        return (
          <div
            key={contract.id || idx}
            className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2 text-xs"
          >
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-900 dark:text-slate-50">
                {title}
              </span>
              <div className="flex items-center gap-2">
                {contract.contract_status && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium">
                    {contract.contract_status}
                  </span>
                )}
                {price && (
                  <span className="font-mono text-slate-500">{price}</span>
                )}
              </div>
            </div>

            {minedName && (
              <div className="text-[11px] text-blue-600 font-medium">
                Client Name Identified: <strong className="underline">{minedName}</strong>
              </div>
            )}

            {reviewClean && (
              <div className="p-2.5 rounded bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900">
                <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-0.5">
                  Freelancer Feedback on Client:
                </span>
                <p className="italic text-slate-700 dark:text-slate-300">
                  &quot;{reviewClean}&quot;
                </p>
              </div>
            )}

            {reviewExcluded && (
              <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 text-slate-500 text-[11px]">
                <span className="font-medium block mb-0.5 text-slate-700 dark:text-slate-300">
                  Client Feedback to Freelancer:
                </span>
                &quot;{reviewExcluded}&quot;
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
