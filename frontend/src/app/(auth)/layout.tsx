import Link from "next/link";
import type { ReactNode } from "react";

/**
 * The shell both auth pages sit in. A narrow column rather than a card: the ledger grid in the
 * background is the surface, and floating a panel above it would hide the thing that gives the
 * page its character.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col px-6 py-10 sm:px-10">
      <header className="rise">
        <Link
          href="/"
          className="inline-flex items-baseline gap-2 outline-none focus-visible:text-accent"
        >
          <span className="font-display text-xl tracking-tight">
            Tradinghub
          </span>
          <span className="h-1 w-1 translate-y-[-0.15rem] rounded-full bg-accent" />
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center py-14">
        <div className="w-full max-w-[26rem]">{children}</div>
      </main>

      <footer className="rise text-[0.6875rem] uppercase tracking-[0.18em] text-ink-faint [animation-delay:240ms]">
        A journal for reviewing your own decisions
      </footer>
    </div>
  );
}
