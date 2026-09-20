"use client";

import { useAuthenticatedUser } from "@/features/auth/hooks";

export default function DashboardPage() {
  const user = useAuthenticatedUser();

  return (
    <>
      <p className="text-[0.6875rem] uppercase tracking-[0.18em] text-ink-faint">
        Signed in as
      </p>
      <h1 className="mt-3 max-w-3xl font-display text-[2.75rem] leading-[1.05] tracking-tight break-words">
        {user.email}
      </h1>
      <p className="mt-8 max-w-md text-sm text-ink-dim">
        No trades yet. The journal starts in the next slice — this page exists
        to prove the session survives a reload.
      </p>
    </>
  );
}
