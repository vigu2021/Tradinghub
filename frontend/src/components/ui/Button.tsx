import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "solid" | "ghost";
};

const VARIANTS = {
  solid:
    "bg-accent text-ground hover:bg-accent/90 disabled:bg-accent/40 disabled:text-ground/70",
  ghost:
    "border border-rule-strong text-ink-dim hover:border-accent hover:text-accent disabled:opacity-50",
} as const;

export function Button({ variant = "solid", ...button }: ButtonProps) {
  return (
    <button
      className={`w-full px-4 py-3 text-[0.6875rem] uppercase tracking-[0.18em] transition-colors outline-none focus-visible:ring-1 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ground disabled:cursor-not-allowed ${VARIANTS[variant]}`}
      {...button}
    />
  );
}
