"use client";

import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import { useLogout, useUser } from "@/features/auth/hooks";
import { messageFor } from "@/lib/api/errors";
import { useRouter } from "next/navigation";

/**
 * The shell every signed-in screen sits in: the mark, the way out, and nothing else. Pages below
 * render their own content only, so a second one does not have to redraw this header.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { data: user, isError: sessionRejected } = useUser();
  const signOut = useLogout();

  useEffect(() => {
    if (sessionRejected) {
      router.replace("/login");
    }
  }, [sessionRejected, router]);

  if (!user) {
    return null;
  }

  return (
    <div className="flex min-h-dvh flex-col px-6 py-10 sm:px-10">
      <header className="rise flex items-baseline justify-between gap-6 border-b border-rule pb-6">
        <Logo />
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

      {signOut.error && (
        <p role="alert" className="mt-6 text-sm text-danger">
          {messageFor(signOut.error)}
        </p>
      )}

      <main className="rise flex-1 py-16 [animation-delay:80ms]">
        {children}
      </main>
    </div>
  );
}
