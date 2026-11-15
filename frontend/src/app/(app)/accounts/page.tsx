"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { CreateAccountForm } from "@/features/ledger/components/AccountForm";
import { AccountList } from "@/features/ledger/components/AccountList";
import type { Account } from "@/features/ledger/types/accounts";

type Panel =
  | { mode: "closed" }
  | { mode: "creating" }
  | { mode: "editing"; account: Account };

export default function AccountsPage() {
  const [panel, setPanel] = useState<Panel>({ mode: "closed" });

  const isOpen = panel.mode !== "closed";

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
          variant={isOpen ? "ghost" : "solid"}
          aria-expanded={isOpen}
          onClick={() =>
            setPanel(isOpen ? { mode: "closed" } : { mode: "creating" })
          }
        >
          {isOpen ? "Close" : "New account"}
        </Button>
      </div>

      <div
        className={`mt-12 grid items-start gap-12 ${isOpen ? "lg:grid-cols-[minmax(0,1fr)_22rem]" : ""}`}
      >
        {isOpen && (
          <section aria-labelledby="account-panel" className="lg:order-last">
            <h2
              id="account-panel"
              className="mb-6 text-xs font-medium tracking-[0.12em] text-ink-faint uppercase"
            >
              {panel.mode === "editing" ? "Edit account" : "New account"}
            </h2>
            {panel.mode === "creating" && <CreateAccountForm />}
          </section>
        )}

        <AccountList
          onAdd={isOpen ? undefined : () => setPanel({ mode: "creating" })}
        />
      </div>
    </>
  );
}
