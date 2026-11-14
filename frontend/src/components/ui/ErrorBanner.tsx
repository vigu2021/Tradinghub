import type { ReactNode } from "react";

/**
 * A failed request's message on a faint danger tint. `role="alert"` has screen
 * readers announce it the moment it appears. Takes children so a caller can add a link or a
 * countdown beside the message.
 */
export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="bg-danger/8 px-3 py-2.5 text-sm text-danger">
      {children}
    </p>
  );
}
