"use client";

import { Button } from "@/components/ui/Button";
import { useLogout, useUser } from "@/features/auth/hooks";
import { messageFor } from "@/lib/api/errors";

export default function DashboardPage() {
  const { data: user, isPending, error } = useUser();
  const signOut = useLogout();

  return (
    <div className="flex min-h-dvh flex-col px-6 py-10 sm:px-10">
      <header className="rise flex items-baseline justify-between gap-6 border-b border-rule pb-6">
        <span className="font-display text-xl tracking-tight">Tradinghub</span>
        <div className="w-32">
          <Button
            variant="ghost"
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
          >
            {signOut.isPending ? "Signing out" : "Sign out"}
          </Button>
        </div>
      </header>

      <main className="rise flex-1 py-16 [animation-delay:80ms]">
        {isPending && (
          <p className="text-sm text-ink-dim">Loading your journal…</p>
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {messageFor(error)}
          </p>
        )}

        {user && (
          <>
            <p className="text-[0.6875rem] uppercase tracking-[0.18em] text-ink-faint">
              Signed in as
            </p>
            <h1 className="mt-3 max-w-3xl font-display text-[2.75rem] leading-[1.05] tracking-tight break-words">
              {user.email}
            </h1>
            <p className="mt-8 max-w-md text-sm text-ink-dim">
              No trades yet. The journal starts in the next slice — this page
              exists to prove the session survives a reload.
            </p>
          </>
        )}

        {signOut.error && (
          <p role="alert" className="mt-6 text-sm text-danger">
            {messageFor(signOut.error)}
          </p>
        )}
      </main>
    </div>
  );
}
