import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/ui/Logo";

/**
 * The shell both auth screens sit in. A narrow column rather than a card: the ledger grid in the
 * background is the surface, and floating a panel above it would hide what gives the page its
 * character.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col px-6 py-8 sm:px-10">
      <header className="rise">
        <Link
          href="/"
          className="inline-block text-ink outline-none transition-colors hover:text-accent focus-visible:text-accent"
        >
          <Logo size="lg" />
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center py-12">
        <div className="w-full max-w-[26rem]">{children}</div>
      </main>

      <footer className="rise text-[0.6875rem] uppercase tracking-[0.18em] text-ink-faint [animation-delay:240ms]">
        A journal for reviewing your own decisions
      </footer>
    </div>
  );
}
