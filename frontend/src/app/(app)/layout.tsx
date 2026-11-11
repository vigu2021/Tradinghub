"use client";

import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Logo } from "@/components/ui/Logo";
import {
  AuthenticatedUserContext,
  useLogout,
  useSession,
} from "@/features/auth/hooks";
import { messageFor } from "@/lib/api/errors";
import { useRouter } from "next/navigation";

/**
 * The shell every signed-in screen sits in: the mark, the way out, and nothing else. Pages below
 * render their own content only, so a second one does not have to redraw this header.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = useSession();
  const signOut = useLogout();

  const anonymous = session.status === "anonymous";

  useEffect(() => {
    if (anonymous) {
      router.replace("/login");
    }
  }, [anonymous, router]);

  if (session.status === "anonymous") {
    return null;
  }

  return (
    <div className="flex min-h-dvh flex-col px-6 py-10 sm:px-10">
      <header className="rise flex items-baseline justify-between gap-6 border-b border-rule pb-6">
        <Logo />
        {session.status === "authenticated" && (
          <Button
            variant="ghost"
            className="w-32"
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
          >
            {signOut.isPending ? "Signing out" : "Sign out"}
          </Button>
        )}
      </header>

      {signOut.error && (
        <div className="mt-6">
          <ErrorBanner>{messageFor(signOut.error)}</ErrorBanner>
        </div>
      )}

      <main className="rise flex-1 py-16 [animation-delay:80ms]">
        {session.status === "unknown" && (
          <p className="text-sm text-ink-faint">Checking your session</p>
        )}

        {session.status === "unreachable" && (
          <div className="max-w-md">
            <p className="text-sm text-ink-dim">Could not reach the server.</p>
            <Button
              variant="ghost"
              className="mt-6 w-32"
              onClick={session.retry}
            >
              Try again
            </Button>
          </div>
        )}

        {session.status === "authenticated" && (
          <AuthenticatedUserContext value={session.user}>
            {children}
          </AuthenticatedUserContext>
        )}
      </main>
    </div>
  );
}
