/** Three candles, the last one closing higher, beside the wordmark. One size everywhere. */
export function Logo() {
  return (
    <span className="inline-flex items-center gap-3">
      <svg
        viewBox="0 0 32 32"
        aria-hidden="true"
        className="h-7 w-7"
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

      <span className="font-display text-2xl leading-none font-semibold tracking-tight">
        Tradinghub
      </span>
    </span>
  );
}
