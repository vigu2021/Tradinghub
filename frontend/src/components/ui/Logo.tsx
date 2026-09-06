type LogoProps = { size?: "md" | "lg" };

const WORDMARK = {
  md: "text-2xl",
  lg: "text-[2rem]",
} as const;

const MARK = {
  md: "h-7 w-7",
  lg: "h-9 w-9",
} as const;

/**
 * Three candles, the last one closing higher. Drawn on the same 4-unit rhythm as the background
 * grid so the mark reads as part of the ledger rather than a badge dropped on top of it.
 */
export function Logo({ size = "md" }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-3">
      <svg
        viewBox="0 0 32 32"
        aria-hidden="true"
        className={MARK[size]}
        fill="none"
        strokeLinecap="square"
      >
        <g stroke="currentColor" strokeWidth="2" opacity="0.45">
          <path d="M6 7v18" />
          <path d="M6 11h0" />
          <rect x="3" y="11" width="6" height="9" fill="currentColor" />
        </g>
        <g stroke="currentColor" strokeWidth="2" opacity="0.45">
          <path d="M16 10v16" />
          <rect x="13" y="15" width="6" height="7" fill="currentColor" />
        </g>
        <g stroke="var(--accent)" strokeWidth="2">
          <path d="M26 4v20" />
          <rect x="23" y="8" width="6" height="12" fill="var(--accent)" />
        </g>
      </svg>

      <span
        className={`font-display leading-none tracking-tight ${WORDMARK[size]}`}
      >
        Tradinghub
      </span>
    </span>
  );
}
