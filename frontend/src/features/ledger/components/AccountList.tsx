"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

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
  const [showArchived, setShowArchived] = useState(false);

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

  const activeAccounts = accounts.filter(
    (account) => account.archived_at === null,
  );
  const archivedAccounts = accounts.filter(
    (account) => account.archived_at !== null,
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
        {activeAccounts.map((account) => (
          <AccountRow key={account.id} account={account} onEdit={onEdit} />
        ))}
      </tbody>

      {archivedAccounts.length > 0 && (
        <tbody>
          <tr>
            <td colSpan={4} className="px-4 pt-7">
              <button
                type="button"
                aria-expanded={showArchived}
                onClick={() => setShowArchived((shown) => !shown)}
                className="inline-flex min-h-11 items-center gap-3 text-xs font-medium tracking-[0.12em] text-ink-faint uppercase hover:text-ink active:text-ink"
              >
                <span
                  aria-hidden
                  className={`size-[7px] border-r-[1.5px] border-b-[1.5px] border-current transition-transform ${showArchived ? "-translate-y-0.5 rotate-45" : "-rotate-45"}`}
                />
                Archived ({archivedAccounts.length})
              </button>
            </td>
          </tr>
        </tbody>
      )}

      {showArchived && (
        <tbody>
          {archivedAccounts.map((account) => (
            <AccountRow key={account.id} account={account} onEdit={onEdit} />
          ))}
        </tbody>
      )}
    </table>
  );
}

type AccountRowProps = {
  account: Account;
  onEdit: (account: Account) => void;
};
function AccountRow({ account, onEdit }: AccountRowProps) {
  return (
    <tr className={account.archived_at ? "text-ink-faint" : "odd:bg-surface"}>
      <td className="px-4 py-3.5">{account.name}</td>
      <td className="px-4 py-3.5 text-ink-dim">
        {ACCOUNT_TYPE_LABELS[account.type]}
      </td>
      <td className="px-4 py-3.5 text-right font-mono tabular-nums">
        {account.balance} <span className="text-ink-faint">{account.unit}</span>
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
  );
}
