"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { accountQueries } from "../api/accounts";
import { ACCOUNT_TYPE_LABELS, type Account } from "../types/accounts";

type AccountListProps = {
  /** Opens the new account form. */
  onAdd: () => void;
};

export function AccountList({ onAdd }: AccountListProps) {
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
          <th className="hidden px-4 pb-3 font-medium sm:table-cell">Type</th>
          <th className="px-4 pb-3 text-right font-medium">Balance</th>
          <th className="pb-3">
            <span className="sr-only">Open</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {activeAccounts.map((account) => (
          <AccountRow key={account.id} account={account} />
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
                  className={`size-1.75 border-r-[1.5px] border-b-[1.5px] border-current transition-transform ${showArchived ? "-translate-y-0.5 rotate-45" : "-rotate-45"}`}
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
            <AccountRow key={account.id} account={account} />
          ))}
        </tbody>
      )}
    </table>
  );
}

type AccountRowProps = {
  account: Account;
};

function AccountRow({ account }: AccountRowProps) {
  const active = account.archived_at === null;

  return (
    <tr
      className={`group relative hover:bg-rule ${active ? "odd:bg-surface" : "text-ink-faint"}`}
    >
      <td className="px-4 py-3.5">
        <Link
          href={`/accounts/${account.id}`}
          className="outline-none after:absolute after:inset-0 focus-visible:underline focus-visible:underline-offset-4"
        >
          {account.name}
        </Link>
      </td>
      <td className="hidden px-4 py-3.5 text-ink-dim sm:table-cell">
        {ACCOUNT_TYPE_LABELS[account.type]}
      </td>
      <td className="px-4 py-3.5 text-right font-mono tabular-nums">
        {account.balance} <span className="text-ink-faint">{account.unit}</span>
      </td>
      <td className="w-12 pr-4 text-right text-ink-faint group-hover:text-accent">
        <ChevronIcon />
      </td>
    </tr>
  );
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      className="ml-auto size-4"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}
