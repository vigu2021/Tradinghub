"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { DisclosureButton } from "@/components/ui/DisclosureButton";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { accountQueries } from "../../api/accounts";
import { ACCOUNT_TYPE_LABELS, type Account } from "../../types/accounts";

/** Groups bigger than this start closed, so one exchange's coins do not push everything else down. */
const OPEN_UP_TO = 5;

export function AccountList() {
  const { data: accounts, isPending, error } = useQuery(accountQueries.list());
  const [showArchived, setShowArchived] = useState(false);
  const [toggled, setToggled] = useState<Record<string, boolean>>({});

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
        <Link
          href="/accounts/new"
          className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline underline-offset-4 hover:text-ink active:text-ink"
        >
          Add your first account
        </Link>
      </div>
    );
  }

  const activeAccounts = accounts.filter(
    (account) => account.archived_at === null,
  );
  const archivedAccounts = accounts.filter(
    (account) => account.archived_at !== null,
  );
  const accountGroups = groupAccounts(activeAccounts);
  const isOpen = (group: AccountGroup) =>
    toggled[group.name] ?? startsOpen(group);

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
      {accountGroups.map((group) => {
        const open = isOpen(group);
        return (
          <tbody key={group.name}>
            <SectionToggle
              label={group.name}
              open={open}
              onToggle={() =>
                setToggled((current) => ({ ...current, [group.name]: !open }))
              }
            />
            {open &&
              group.accounts.map((account) => (
                <AccountRow key={account.id} account={account} />
              ))}
          </tbody>
        );
      })}

      {archivedAccounts.length > 0 && (
        <tbody>
          <SectionToggle
            label={`Archived (${archivedAccounts.length})`}
            open={showArchived}
            onToggle={() => setShowArchived((shown) => !shown)}
            muted
          />
          {showArchived &&
            archivedAccounts.map((account) => (
              <AccountRow key={account.id} account={account} />
            ))}
        </tbody>
      )}
    </table>
  );
}

type SectionToggleProps = {
  label: string;
  open: boolean;
  onToggle: () => void;
  muted?: boolean;
};

/** A heading row spanning the table that opens and closes the rows under it. */
function SectionToggle({ label, open, onToggle, muted }: SectionToggleProps) {
  return (
    <tr>
      <td colSpan={4} className="px-4 pt-6 pb-1">
        <DisclosureButton
          open={open}
          onToggle={onToggle}
          className={`text-xs tracking-[0.12em] uppercase ${
            muted ? "font-medium text-ink-faint" : "font-semibold text-ink"
          }`}
        >
          {label}
        </DisclosureButton>
      </td>
    </tr>
  );
}

type AccountRowProps = {
  account: Account;
};

function AccountRow({ account }: AccountRowProps) {
  const active = account.archived_at === null;

  return (
    <tr
      className={`group relative hover:bg-rule ${active ? "even:bg-surface" : "text-ink-faint"}`}
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

type AccountGroup = {
  name: string;
  accounts: Account[];
};

/** One group per exact group name, in alphabetical order; accounts keep the API's order by name. */
function groupAccounts(accounts: Account[]): AccountGroup[] {
  const byGroup = Map.groupBy(accounts, (account) => account.group_name);
  const groups = [...byGroup].map(([name, members]) => ({
    name,
    accounts: members,
  }));
  return groups.sort((a, b) => a.name.localeCompare(b.name));
}

function startsOpen(group: AccountGroup): boolean {
  return group.accounts.length <= OPEN_UP_TO;
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
