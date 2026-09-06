import type { InputHTMLAttributes, ReactNode, Ref } from "react";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string;
  ref?: Ref<HTMLInputElement>;
};

/**
 * A labelled input drawn as a ledger line: no box, one hairline underneath that lights up on
 * focus. The hint stays visible rather than appearing only after a rejection.
 */
export function Field({ id, label, hint, error, ref, ...input }: FieldProps) {
  // The error supersedes the hint rather than stacking under it: "at least 8 characters" and
  // "use at least 8 characters" one above the other is the same sentence twice.
  const showHint = Boolean(hint) && !error;
  const hintId = showHint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="group">
      <label
        htmlFor={id}
        className={`block text-[0.6875rem] uppercase tracking-[0.18em] transition-colors ${
          error
            ? "text-danger"
            : "text-ink-faint group-focus-within:text-accent"
        }`}
      >
        {label}
      </label>

      <input
        id={id}
        ref={ref}
        aria-invalid={Boolean(error)}
        aria-describedby={
          [errorId, hintId].filter(Boolean).join(" ") || undefined
        }
        className={`mt-2 w-full border-0 border-b bg-transparent pb-2 text-[0.9375rem] text-ink caret-accent outline-none transition-colors placeholder:text-ink-faint focus:border-accent ${
          error ? "border-danger" : "border-rule-strong"
        }`}
        {...input}
      />

      {showHint && (
        <p id={hintId} className="mt-2 text-xs text-ink-faint">
          {hint}
        </p>
      )}

      {error && (
        <p id={errorId} role="alert" className="mt-2 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
