"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { accountQueries } from "../api/accounts";
import { ACCOUNT_TYPE_LABELS, type Account } from "../types/accounts";

type AccountListProps = {
  /** Opens the new account form. */
  onAdd: () => void;
  /** Opens the edit form for the account whose Edit button was pressed. */
  onEdit: (account: Account) => void;
};

export function AccountList({ onAdd, onEdit }: AccountListProps) {
  const { data: accounts, isPending, error } = useQuery(accountQueries.list());

  if (isPending) {
    return <p className="text-sm text-ink-faint">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner>{messageFor(error)}</ErrorBanner>;
  }
  if (accounts.length === 0) {
    return (
      <div className="bg-surface px-6 py-12 sm:px-10">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          No accounts yet
        </h2>
        <p className="mt-3 max-w-prose text-sm text-ink-dim">
          An account is anywhere money sits: a bank, an exchange, a broker. Add
          one and everything you record against it adds up here.
        </p>
        <button
          type="button"
          onClick={onAdd}
          className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline underline-offset-4 hover:text-ink active:text-ink"
        >
          Add your first account
        </button>
      </div>
    );
  }

  const activeFirst = accounts.toSorted(
    (a, b) => Number(Boolean(a.archived_at)) - Number(Boolean(b.archived_at)),
  );

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs font-medium tracking-[0.12em] text-ink-faint uppercase">
          <th className="px-4 pb-3 font-medium">Name</th>
          <th className="px-4 pb-3 font-medium">Type</th>
          <th className="px-4 pb-3 text-right font-medium">Balance</th>
          <th className="pb-3">
            <span className="sr-only">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {activeFirst.map((account) => (
          <tr
            key={account.id}
            className={`odd:bg-surface ${account.archived_at ? "text-ink-faint" : ""}`}
          >
            <td className="px-4 py-3.5">
              {account.name}
              {account.archived_at && (
                <span className="ml-3 bg-rule px-1.5 py-0.5 text-[0.6875rem] font-medium text-ink-dim">
                  Archived
                </span>
              )}
            </td>
            <td className="px-4 py-3.5 text-ink-dim">
              {ACCOUNT_TYPE_LABELS[account.type]}
            </td>
            <td className="px-4 py-3.5 text-right font-mono tabular-nums">
              {account.balance}{" "}
              <span className="text-ink-faint">{account.unit}</span>
            </td>
            <td className="py-0.5 pr-2 text-right">
              <button
                type="button"
                aria-label={`Edit ${account.name}`}
                onClick={() => onEdit(account)}
                className="inline-flex min-h-11 items-center px-2 text-sm font-semibold text-ink-dim underline-offset-4 hover:text-accent hover:underline active:text-accent"
              >
                Edit
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
