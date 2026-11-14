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
      <p className="border border-dashed border-rule-strong px-6 py-10 text-center text-sm text-ink-dim">
        Create new account here
      </p>
    );
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-rule-strong text-left text-[0.6875rem] uppercase tracking-[0.18em] text-ink-faint">
          <th className="pr-4 pb-3 font-normal">Name</th>
          <th className="pr-4 pb-3 font-normal">Type</th>
          <th className="pb-3 text-right font-normal">Balance</th>
        </tr>
      </thead>
      <tbody>
        {accounts.map((account) => (
          <tr
            key={account.id}
            className={`border-b border-rule ${account.archived_at ? "text-ink-faint" : ""}`}
          >
            <td className="py-4 pr-4">
              {account.name}
              {account.archived_at && (
                <span className="ml-3 border border-rule-strong px-1.5 py-0.5 text-[0.625rem] uppercase tracking-[0.16em] text-ink-faint">
                  Archived
                </span>
              )}
            </td>
            <td className="py-4 pr-4 text-ink-dim">{account.type}</td>
            <td className="py-4 text-right tabular-nums">
              {account.balance}{" "}
              <span className="text-ink-faint">{account.unit}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
