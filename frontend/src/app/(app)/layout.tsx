"use client";

import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
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
          <div className="w-32">
            <Button
              variant="ghost"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              {signOut.isPending ? "Signing out" : "Sign out"}
            </Button>
          </div>
        )}
      </header>

      {signOut.error && (
        <p role="alert" className="mt-6 text-sm text-danger">
          {messageFor(signOut.error)}
        </p>
      )}

      <main className="rise flex-1 py-16 [animation-delay:80ms]">
        {session.status === "unknown" && (
          <p className="text-sm text-ink-faint">Checking your session</p>
        )}

        {session.status === "unreachable" && (
          <div className="max-w-md">
            <p className="text-sm text-ink-dim">Could not reach the server.</p>
            <div className="mt-6 w-32">
              <Button variant="ghost" onClick={session.retry}>
                Try again
              </Button>
            </div>
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
