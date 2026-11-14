import Link from "next/link";

import { Logo } from "@/components/ui/Logo";

export const metadata = {
  title: "Tradinghub · A clearer record of every decision",
};

const PRIMARY_LINK =
  "inline-flex min-h-11 items-center whitespace-nowrap bg-accent px-5 text-sm font-semibold text-accent-ink transition-colors outline-none hover:bg-accent/90 focus-visible:ring-1 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ground";
const QUIET_LINK =
  "inline-flex min-h-11 items-center whitespace-nowrap text-sm font-medium text-ink-dim transition-colors outline-none hover:text-ink focus-visible:text-ink";
const CAPTION =
  "text-xs font-medium tracking-[0.12em] text-ink-faint uppercase";

/** Sample figures for the preview. They show the product; nothing here is a user's data. */
const STATEMENT = [
  { label: "Opening, 1 Nov", amount: "10,692.60" },
  { label: "Money in", amount: "+3,000.00", positive: true },
  { label: "Money out", amount: "-1,217.40" },
  { label: "Closing, 30 Nov", amount: "12,475.20" },
] as const;

const ENTRIES = [
  {
    date: "28 Nov",
    what: "Rent",
    account: "Chase",
    kind: "expense",
    amount: "-900.00",
    unit: "GBP",
  },
  {
    date: "25 Nov",
    what: "Salary",
    account: "Monzo",
    kind: "income",
    amount: "+3,000.00",
    unit: "GBP",
  },
  {
    date: "18 Nov",
    what: "Bought bitcoin",
    account: "Binance",
    kind: "transfer",
    amount: "+0.00512000",
    unit: "BTC",
  },
  {
    date: "18 Nov",
    what: "Exchange fee",
    account: "Chase",
    kind: "expense",
    amount: "-2.50",
    unit: "GBP",
  },
  {
    date: "14 Nov",
    what: "Groceries",
    account: "Monzo",
    kind: "expense",
    amount: "-64.20",
    unit: "GBP",
  },
] as const;

const IDEAS = [
  {
    title: "Every account in its own unit",
    body: "Cash, crypto and stock accounts, each kept in GBP, BTC or whatever it really holds. Nothing is converted behind your back.",
  },
  {
    title: "Money in, out and between",
    body: "Income and spending, and transfers between your own accounts, with any fee recorded as what it is: money spent.",
  },
  {
    title: "Review, not just record",
    body: "See where it went by period and category, then look back at the decisions behind the numbers.",
  },
] as const;

const NEXT = [
  "Net worth in one currency",
  "Binance import",
  "Trade review",
] as const;

/**
 * The public front door. Static, so it arrives complete in the first response; a signed-in visitor
 * who follows "Sign in" is moved on to the dashboard by the auth layout.
 */
export default function Home() {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-6 py-8 sm:px-10">
      <header className="rise flex items-center justify-between gap-6">
        <Logo />
        <nav className="flex items-center gap-4 sm:gap-6">
          <Link href="/login" className={QUIET_LINK}>
            Sign in
          </Link>
          <span className="hidden sm:block">
            <Link href="/register" className={PRIMARY_LINK}>
              Get started
            </Link>
          </span>
        </nav>
      </header>

      <main className="flex-1">
        <section className="pt-24 pb-16 sm:pt-32">
          <h1 className="rise max-w-[13ch] font-display text-[clamp(3rem,8vw,6rem)] leading-[0.95] font-semibold tracking-[-0.03em] [animation-delay:80ms]">
            A clearer record of every decision.
          </h1>
          <p className="rise mt-8 max-w-[46ch] text-lg text-ink-dim [animation-delay:160ms]">
            Tradinghub is a private journal for your money. Record every
            account, transaction and transfer, then read your own decisions back
            like a statement you wrote.
          </p>
          <div className="rise mt-10 flex flex-wrap items-center gap-x-8 gap-y-4 [animation-delay:240ms]">
            <Link href="/register" className={PRIMARY_LINK}>
              Start your journal
            </Link>
            <Link href="/login" className={QUIET_LINK}>
              I already have an account
            </Link>
          </div>
        </section>

        <section
          aria-label="What the journal looks like"
          className="rise bg-surface p-6 sm:p-10 [animation-delay:360ms]"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <p className={CAPTION}>November statement</p>
            <p className="text-sm text-ink-faint">All accounts, in GBP</p>
          </div>

          <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-6 md:grid-cols-4">
            {STATEMENT.map(({ label, amount, ...tone }) => (
              <div key={label}>
                <dt className={CAPTION}>{label}</dt>
                <dd
                  className={`mt-2 font-mono text-2xl tabular-nums sm:text-3xl ${
                    "positive" in tone ? "text-positive" : ""
                  }`}
                >
                  {amount}
                </dd>
              </div>
            ))}
          </dl>

          <table className="mt-10 w-full text-sm">
            <thead>
              <tr className={`${CAPTION} text-left`}>
                <th className="px-3 pb-3 font-medium">Date</th>
                <th className="px-3 pb-3 font-medium">Entry</th>
                <th className="hidden px-3 pb-3 font-medium sm:table-cell">
                  Account
                </th>
                <th className="hidden px-3 pb-3 font-medium md:table-cell">
                  Kind
                </th>
                <th className="px-3 pb-3 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {ENTRIES.map((entry) => (
                <tr
                  key={`${entry.date}-${entry.what}`}
                  className="odd:bg-ground"
                >
                  <td className="px-3 py-3 text-ink-dim">{entry.date}</td>
                  <td className="px-3 py-3">{entry.what}</td>
                  <td className="hidden px-3 py-3 text-ink-dim sm:table-cell">
                    {entry.account}
                  </td>
                  <td className="hidden px-3 py-3 text-ink-faint md:table-cell">
                    {entry.kind}
                  </td>
                  <td
                    className={`px-3 py-3 text-right font-mono tabular-nums ${
                      entry.amount.startsWith("+") ? "text-positive" : ""
                    }`}
                  >
                    {entry.amount}
                    <span className="ml-1.5 text-ink-faint">{entry.unit}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="grid gap-12 py-24 md:grid-cols-3">
          {IDEAS.map((idea, index) => (
            <div key={idea.title}>
              <p className="font-mono text-sm text-accent">0{index + 1}</p>
              <h2 className="mt-4 text-xl font-semibold tracking-tight">
                {idea.title}
              </h2>
              <p className="mt-3 text-ink-dim">{idea.body}</p>
            </div>
          ))}
        </section>

        <section className="flex flex-wrap items-baseline gap-x-8 gap-y-3 pb-24">
          <p className={CAPTION}>Next</p>
          {NEXT.map((item) => (
            <p key={item} className="text-ink-dim">
              {item}
            </p>
          ))}
        </section>

        <section className="bg-surface px-6 py-16 sm:px-10">
          <h2 className="max-w-[18ch] text-[clamp(2rem,4vw,3rem)] leading-tight font-semibold tracking-tight">
            Start the record today.
          </h2>
          <p className="mt-4 max-w-[44ch] text-ink-dim">
            An email and a password, nothing else. Your first account takes ten
            seconds.
          </p>
          <Link href="/register" className={`${PRIMARY_LINK} mt-8`}>
            Start your journal
          </Link>
        </section>
      </main>

      <footer className="flex flex-wrap justify-between gap-4 pt-10 text-sm text-ink-faint">
        <span>A journal for reviewing your own decisions.</span>
        <span>Tradinghub</span>
      </footer>
    </div>
  );
}
