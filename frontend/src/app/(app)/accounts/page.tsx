"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { CreateAccountForm } from "@/features/ledger/components/AccountForm";
import { AccountList } from "@/features/ledger/components/AccountList";

export default function AccountsPage() {
  const [creating, setCreating] = useState(false);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-display text-[2.75rem] leading-none tracking-tight">
            Accounts
          </h1>
          <p className="mt-3 text-sm text-ink-dim">
            Every place money sits. Balances are the sum of what you recorded.
          </p>
        </div>
        <Button
          variant={creating ? "ghost" : "solid"}
          aria-expanded={creating}
          onClick={() => setCreating((open) => !open)}
        >
          {creating ? "Close" : "New account"}
        </Button>
      </div>

      {creating && (
        <section
          aria-label="New account"
          className="mt-10 max-w-xl border border-rule bg-ground-raised/60 p-6"
        >
          <CreateAccountForm />
        </section>
      )}

      <div className="mt-12">
        <AccountList />
      </div>
    </>
  );
}
