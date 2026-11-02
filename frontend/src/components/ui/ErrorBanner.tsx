import type { ReactNode } from "react";

/**
 * A failed request's message, marked in the margin like a correction. `role="alert"` has screen
 * readers announce it the moment it appears. Takes children so a caller can add a link or a
 * countdown beside the message.
 */
export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="border-l-2 border-danger bg-danger/5 py-2 pl-3 text-sm text-danger"
    >
      {children}
    </p>
  );
}
