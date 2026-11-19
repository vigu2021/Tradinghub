import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const VARIANTS = {
  solid:
    "bg-accent text-accent-ink hover:bg-accent/90 active:bg-accent/80 disabled:bg-accent/40",
  ghost:
    "bg-surface text-ink hover:bg-rule active:bg-rule-strong disabled:text-ink-faint",
} as const;

type Variant = keyof typeof VARIANTS;

/** Sizes to its text. A caller sets width or spacing with `className`, which is added last. */
export function Button({
  variant = "solid",
  className = "",
  ...button
}: ButtonProps) {
  return <button className={buttonClasses(variant, className)} {...button} />;
}

/** The same look for a link that leads somewhere, so it can stay a real link. */
export function buttonClasses(
  variant: Variant = "solid",
  className = "",
): string {
  return `inline-flex min-h-11 items-center justify-center px-4 py-2.5 text-sm font-semibold transition-colors outline-none focus-visible:ring-1 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ground disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`;
}
