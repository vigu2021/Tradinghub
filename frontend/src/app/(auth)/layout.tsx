"use client";

import Link from "next/link";
import { useEffect, type ReactNode } from "react";

import { Logo } from "@/components/ui/Logo";
import { useRouter } from "next/navigation";
import { useSession } from "@/features/auth/hooks";

/**
 * The shell both auth screens sit in: the tagline set large on one side, the form on the other.
 * No card around the form; the page itself is the surface.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = useSession();
  const authenticated = session.status === "authenticated";

  useEffect(() => {
    if (authenticated) {
      router.replace("/dashboard");
    }
  }, [authenticated, router]);

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-6 py-8 sm:px-10">
      <header className="rise">
        <Link
          href="/"
          className="inline-block text-ink outline-none transition-colors hover:text-accent focus-visible:text-accent"
        >
          <Logo size="lg" />
        </Link>
      </header>

      <main className="grid flex-1 items-center gap-16 py-12 md:grid-cols-2">
        <p className="rise hidden max-w-[14ch] font-display text-[2.5rem] leading-tight font-semibold tracking-tight text-ink-dim md:block [animation-delay:160ms]">
          A journal for reviewing your own decisions.
        </p>
        <div className="w-full max-w-[26rem]">{children}</div>
      </main>
    </div>
  );
}
