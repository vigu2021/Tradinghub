"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/accounts", label: "Accounts" },
] as const;

/**
 * The shell every signed-in screen sits in: the mark, the sections, and the way out. Pages below
 * render their own content only, so a second one does not have to redraw this header.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
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
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-6 py-8 sm:px-10">
      <header className="rise flex flex-wrap items-center justify-between gap-6">
        <Logo />
        {session.status === "authenticated" && (
          <nav className="flex gap-6 text-sm">
            {NAV.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
                className="py-1 text-ink-dim transition-colors hover:text-ink aria-[current=page]:font-semibold aria-[current=page]:text-ink aria-[current=page]:shadow-[inset_0_-2px_0_var(--accent)]"
              >
                {label}
              </Link>
            ))}
          </nav>
        )}
        {session.status === "authenticated" && (
          <Button
            variant="ghost"
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
            <Button variant="ghost" className="mt-6" onClick={session.retry}>
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
