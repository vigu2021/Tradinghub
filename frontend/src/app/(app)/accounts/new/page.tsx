"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { NewAccountForm } from "@/features/ledger/components/accounts/NewAccountForm";

export default function NewAccountPage() {
  const router = useRouter();

  return (
    <>
      <Link
        href="/accounts"
        className="inline-flex min-h-11 items-center text-sm font-semibold text-ink-dim underline-offset-4 hover:text-accent hover:underline"
      >
        ‹ Accounts
      </Link>
      <h1 className="mt-4 font-display text-[2rem] leading-none font-semibold tracking-tight sm:mt-8 sm:text-[2.5rem]">
        New account
      </h1>
      <p className="mt-3 text-sm text-ink-dim">
        Anywhere money sits: a bank, an exchange, a broker.
      </p>
      <div className="mt-8 max-w-md">
        <NewAccountForm
          onCreated={(account) => router.push(`/accounts/${account.id}`)}
          onCancel={() => router.push("/accounts")}
        />
      </div>
    </>
  );
}
