import type {
  InputHTMLAttributes,
  ReactNode,
  Ref,
  SelectHTMLAttributes,
} from "react";

type FrameProps = {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string;
  /** Added to the wrapper, for spacing and width. */
  className?: string;
};

type FieldProps = FrameProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
    ref?: Ref<HTMLInputElement>;
  };

type SelectFieldProps = FrameProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, "className"> & {
    ref?: Ref<HTMLSelectElement>;
  };

const CONTROL =
  "mt-2 w-full border bg-surface px-3 py-2.5 text-[0.9375rem] text-ink caret-accent outline-none transition-colors placeholder:text-ink-faint focus:border-accent";

/**
 * A labelled input on a filled surface, with no outline until it has focus or an error. The hint
 * stays visible rather than appearing only after a rejection.
 */
export function Field({
  id,
  label,
  hint,
  error,
  className,
  ref,
  ...input
}: FieldProps) {
  const described = describedBy(id, hint, error);
  return (
    <FieldFrame
      id={id}
      label={label}
      hint={hint}
      error={error}
      className={className}
    >
      <input
        id={id}
        ref={ref}
        aria-invalid={Boolean(error)}
        aria-describedby={described}
        className={`${CONTROL} ${error ? "border-danger" : "border-transparent"}`}
        {...input}
      />
    </FieldFrame>
  );
}

/** The same filled control as `Field`, choosing from `<option>` children. */
export function SelectField({
  id,
  label,
  hint,
  error,
  className,
  ref,
  children,
  ...select
}: SelectFieldProps) {
  const described = describedBy(id, hint, error);
  return (
    <FieldFrame
      id={id}
      label={label}
      hint={hint}
      error={error}
      className={className}
    >
      <select
        id={id}
        ref={ref}
        aria-invalid={Boolean(error)}
        aria-describedby={described}
        className={`${CONTROL} ${error ? "border-danger" : "border-transparent"}`}
        {...select}
      >
        {children}
      </select>
    </FieldFrame>
  );
}

function FieldFrame({
  id,
  label,
  hint,
  error,
  className = "",
  children,
}: FrameProps & { children: ReactNode }) {
  return (
    <div className={`group ${className}`}>
      <label
        htmlFor={id}
        className={`block text-[0.8125rem] font-medium transition-colors ${
          error ? "text-danger" : "text-ink-dim group-focus-within:text-ink"
        }`}
      >
        {label}
      </label>

      {children}

      {showsHint(hint, error) && (
        <p id={`${id}-hint`} className="mt-2 text-xs text-ink-faint">
          {hint}
        </p>
      )}

      {error && (
        <p id={`${id}-error`} role="alert" className="mt-2 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

// The error supersedes the hint rather than stacking under it: "at least 8 characters" and
// "use at least 8 characters" one above the other is the same sentence twice.
function showsHint(hint: ReactNode, error: string | undefined): boolean {
  return Boolean(hint) && !error;
}

function describedBy(
  id: string,
  hint: ReactNode,
  error: string | undefined,
): string | undefined {
  const ids = [
    error ? `${id}-error` : null,
    showsHint(hint, error) ? `${id}-hint` : null,
  ];
  return ids.filter(Boolean).join(" ") || undefined;
}
