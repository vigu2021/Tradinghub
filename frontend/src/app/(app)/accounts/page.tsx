"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { AccountForm } from "@/features/ledger/components/AccountForm";
import { AccountList } from "@/features/ledger/components/AccountList";

export default function AccountsPage() {
  const [creating, setCreating] = useState(false);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-display text-[2rem] leading-none font-semibold tracking-tight sm:text-[2.5rem]">
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

      <div
        className={`mt-12 grid items-start gap-12 ${creating ? "lg:grid-cols-[minmax(0,1fr)_22rem]" : ""}`}
      >
        {creating && (
          <section aria-labelledby="new-account" className="lg:order-last">
            <h2
              id="new-account"
              className="mb-6 text-xs font-medium tracking-[0.12em] text-ink-faint uppercase"
            >
              New account
            </h2>
            <AccountForm mode="creating" />
          </section>
        )}

        <AccountList onAdd={() => setCreating(true)} />
      </div>
    </>
  );
}
