"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { accountQueries } from "../api/accounts";

export function AccountList() {
  const { data: accounts, isPending, error } = useQuery(accountQueries.list());

  if (isPending) {
    return <p className="text-sm text-ink-faint">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner>{messageFor(error)}</ErrorBanner>;
  }
  if (accounts.length === 0) {
    return (
      <p className="bg-surface px-6 py-10 text-center text-sm text-ink-dim">
        Create new account here
      </p>
    );
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs font-medium tracking-[0.12em] text-ink-faint uppercase">
          <th className="px-4 pb-3 font-medium">Name</th>
          <th className="px-4 pb-3 font-medium">Type</th>
          <th className="px-4 pb-3 text-right font-medium">Balance</th>
        </tr>
      </thead>
      <tbody>
        {accounts.map((account) => (
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
            <td className="px-4 py-3.5 text-ink-dim">{account.type}</td>
            <td className="px-4 py-3.5 text-right font-mono tabular-nums">
              {account.balance}{" "}
              <span className="text-ink-faint">{account.unit}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
