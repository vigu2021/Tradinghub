import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "solid" | "ghost";
};

const VARIANTS = {
  solid: "bg-accent text-accent-ink hover:bg-accent/90 disabled:bg-accent/40",
  ghost: "bg-surface text-ink hover:bg-rule disabled:text-ink-faint",
} as const;

/** Sizes to its text. A caller sets width or spacing with `className`, which is added last. */
export function Button({
  variant = "solid",
  className = "",
  ...button
}: ButtonProps) {
  return (
    <button
      className={`px-4 py-2.5 text-sm font-semibold transition-colors outline-none focus-visible:ring-1 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ground disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...button}
    />
  );
}
