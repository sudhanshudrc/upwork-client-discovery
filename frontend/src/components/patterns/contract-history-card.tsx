import { Layers } from 'lucide-react';
import type { ContractRecord } from '@/services/api';

interface ContractHistoryCardProps {
  contracts?: ContractRecord[];
}

export function ContractHistoryCard({ contracts = [] }: ContractHistoryCardProps) {
  if (contracts.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-[#656C43] dark:text-[#BAC095] border border-dashed border-[#BAC095] rounded-lg space-y-2">
        <div className="font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
          No contract history loaded yet
        </div>
        <p className="text-[11px] text-[#656C43] dark:text-[#BAC095] max-w-md mx-auto leading-relaxed">
          Upwork masks client names on jobs by default. Past freelancer reviews frequently mention client names directly. Click &quot;Fetch History&quot; above to load past feedback.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-[#636B2F] dark:text-[#D4DE95]">
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
            className="p-3.5 rounded-lg border border-[#E1E4D3] dark:border-[#2E331E] bg-white dark:bg-[#202414] space-y-2 text-xs"
          >
            <div className="flex justify-between items-center">
              <span className="font-semibold text-[#3D4127] dark:text-[#F8F9F3]">
                {title}
              </span>
              <div className="flex items-center gap-2">
                {contract.contract_status && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-[#EFF2E3] dark:bg-[#15180E] text-[#656C43] dark:text-[#BAC095] font-medium">
                    {contract.contract_status}
                  </span>
                )}
                {price && (
                  <span className="font-mono text-[#656C43] dark:text-[#BAC095]">{price}</span>
                )}
              </div>
            </div>

            {minedName && (
              <div className="text-[11px] text-[#636B2F] dark:text-[#D4DE95] font-medium">
                Client Name Identified: <strong className="underline">{minedName}</strong>
              </div>
            )}

            {reviewClean && (
              <div className="p-2.5 rounded bg-[#EFF4DC]/40 dark:bg-[#2B3118]/40 border border-[#636B2F]/30">
                <span className="font-semibold text-[#3D4127] dark:text-[#F8F9F3] block mb-0.5">
                  Freelancer Feedback on Client:
                </span>
                <p className="italic text-[#3D4127] dark:text-[#F8F9F3]">
                  &quot;{reviewClean}&quot;
                </p>
              </div>
            )}

            {reviewExcluded && (
              <div className="p-2.5 rounded bg-[#EFF2E3] dark:bg-[#15180E] border border-[#BAC095] dark:border-[#2E331E] text-[#656C43] dark:text-[#BAC095] text-[11px]">
                <span className="font-medium block mb-0.5 text-[#4D5333] dark:text-[#DCE1C4]">
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
