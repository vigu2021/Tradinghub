"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { transactionQueries } from "../api/transactions";
import type { Account } from "../types/accounts";
import type { TransactionKind } from "../types/transactions";

type RecentTransactionsProps = {
  account: Account;
};

const LIMIT = 5;

const KIND_LABELS: Record<TransactionKind, string> = {
  income: "Income",
  expense: "Expense",
  transfer: "Transfer",
};

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
});

/** The account's latest transactions, newest first. */
export function RecentTransactions({ account }: RecentTransactionsProps) {
  const { data, isPending, error } = useQuery({
    ...transactionQueries.list({ account_id: account.id, limit: LIMIT }),
    // Another account's rows are no stand-in for this one's.
    placeholderData: undefined,
  });

  if (isPending) {
    return <p className="text-sm text-ink-faint">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner>{messageFor(error)}</ErrorBanner>;
  }
  if (data.items.length === 0) {
    return (
      <p className="bg-surface px-4 py-3.5 text-sm text-ink-dim">
        No transactions yet.
      </p>
    );
  }

  return (
    <>
      <table className="w-full border-collapse text-sm">
        <thead className="hidden sm:table-header-group">
          <tr className="text-left text-xs font-medium tracking-[0.12em] text-ink-faint uppercase">
            <th className="px-4 pb-3 font-medium">Date</th>
            <th className="px-4 pb-3 font-medium">Description</th>
            <th className="px-4 pb-3 text-right font-medium">Amount</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((transaction) => {
            const day = DAY.format(new Date(transaction.occurred_at));
            return (
              <tr key={transaction.id} className="odd:bg-surface">
                <td className="hidden w-20 px-4 py-3.5 text-ink-dim sm:table-cell">
                  {day}
                </td>
                <td className="px-4 py-3 sm:py-3.5">
                  <span className="block first-letter:uppercase">
                    {transaction.category ?? KIND_LABELS[transaction.kind]}
                  </span>
                  <span className="mt-0.5 block text-xs text-ink-faint sm:hidden">
                    {day}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-right font-mono tabular-nums">
                  {transaction.amount}{" "}
                  <span className="text-ink-faint">{account.unit}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {data.total > data.items.length && (
        <p className="mt-3 text-sm text-ink-dim">
          Latest {data.items.length} of {data.total}.
        </p>
      )}
    </>
  );
}
