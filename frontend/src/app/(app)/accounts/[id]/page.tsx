"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { accountQueries } from "@/features/ledger/api/accounts";
import { AccountForm } from "@/features/ledger/components/AccountForm";
import { ArchiveAccount } from "@/features/ledger/components/ArchiveAccount";
import { RecentTransactions } from "@/features/ledger/components/RecentTransactions";
import {
  ACCOUNT_TYPE_LABELS,
  type Account,
} from "@/features/ledger/types/accounts";
import { messageFor } from "@/lib/api/errors";

const CAPTION =
  "text-xs font-medium tracking-[0.12em] text-ink-faint uppercase";

export default function AccountPage() {
  const { id } = useParams<{ id: string }>();
  const { data: accounts, isPending, error } = useQuery(accountQueries.list());
  const [editing, setEditing] = useState(false);

  if (isPending) {
    return <p className="text-sm text-ink-faint">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner>{messageFor(error)}</ErrorBanner>;
  }

  const account = accounts.find((candidate) => candidate.id === Number(id));
  if (!account) {
    return (
      <div>
        <h1 className="font-display text-[2rem] leading-none font-semibold tracking-tight">
          No account here
        </h1>
        <p className="mt-3 text-sm text-ink-dim">
          Check the address, or go back to your accounts.
        </p>
        <BackLink />
      </div>
    );
  }

  return (
    <>
      <BackLink />

      <section aria-label="Account" className="mt-4 sm:mt-8">
        <AccountHeader account={account} />
      </section>

      <section aria-labelledby="recent" className="mt-10 sm:mt-14">
        <h2 id="recent" className={`${CAPTION} mb-4`}>
          Recent activity
        </h2>
        <RecentTransactions account={account} />
      </section>

      <section aria-labelledby="settings" className="mt-12 sm:mt-16">
        <h2 id="settings" className={`${CAPTION} mb-2`}>
          Settings
        </h2>
        <div className="divide-y divide-rule border-y border-rule">
          <div className="py-4">
            {editing ? (
              <AccountForm
                key={account.id}
                mode="editing"
                account={account}
                onClose={() => setEditing(false)}
              />
            ) : (
              <DetailsRow account={account} onEdit={() => setEditing(true)} />
            )}
          </div>
          <div className="py-4">
            <ArchiveAccount account={account} />
          </div>
        </div>
      </section>
    </>
  );
}

type AccountHeaderProps = {
  account: Account;
};

function AccountHeader({ account }: AccountHeaderProps) {
  return (
    <div className="grid gap-x-10 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <div className="min-w-0">
        <p className={CAPTION}>
          {ACCOUNT_TYPE_LABELS[account.type]} · {account.unit}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="font-display text-[1.75rem] leading-tight font-semibold tracking-tight break-words sm:text-[2.5rem]">
            {account.name}
          </h1>
          {account.archived_at !== null && (
            <span className="bg-rule px-1.5 py-0.5 text-[0.6875rem] font-medium tracking-[0.08em] text-ink-dim uppercase">
              Archived
            </span>
          )}
        </div>
      </div>
      <div className="mt-5 min-w-0 sm:mt-0 sm:text-right">
        <p className={CAPTION}>Balance</p>
        <p className="mt-2 font-mono text-[2.25rem] leading-none break-all tabular-nums sm:text-[2.75rem]">
          {account.balance}{" "}
          <span className="text-ink-faint">{account.unit}</span>
        </p>
      </div>
    </div>
  );
}

type DetailsRowProps = {
  account: Account;
  onEdit: () => void;
};

function DetailsRow({ account, onEdit }: DetailsRowProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-semibold">Details</p>
        <p className="mt-0.5 break-words text-ink-dim">
          {account.name} · {account.unit} · {ACCOUNT_TYPE_LABELS[account.type]}
        </p>
      </div>
      <Button variant="ghost" className="min-w-24 shrink-0" onClick={onEdit}>
        Edit
      </Button>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/accounts"
      className="mt-6 inline-flex min-h-11 items-center text-sm font-semibold text-ink-dim underline-offset-4 first:mt-0 hover:text-accent hover:underline"
    >
      ‹ Accounts
    </Link>
  );
}
