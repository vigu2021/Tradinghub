import Link from "next/link";

import { buttonClasses } from "@/components/ui/Button";
import { AccountList } from "@/features/ledger/components/accounts/AccountList";

export default function AccountsPage() {
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
        <Link href="/accounts/new" className={buttonClasses()}>
          New account
        </Link>
      </div>

      <div className="mt-12">
        <AccountList />
      </div>
    </>
  );
}
