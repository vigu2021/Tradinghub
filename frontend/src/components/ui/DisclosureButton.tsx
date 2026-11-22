import type { ButtonHTMLAttributes } from "react";

type DisclosureButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "type" | "onClick"
> & {
  open: boolean;
  onToggle: () => void;
};

/**
 * A full-width button with an arrow that turns as it opens and closes the content it controls. The
 * caller styles the text with `className` and decides what to show when open.
 */
export function DisclosureButton({
  open,
  onToggle,
  className = "",
  children,
  ...button
}: DisclosureButtonProps) {
  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={onToggle}
      className={`flex min-h-11 w-full items-center gap-3 text-left hover:text-accent active:text-accent ${className}`}
      {...button}
    >
      <span
        aria-hidden
        className={`size-1.75 shrink-0 border-r-[1.5px] border-b-[1.5px] border-current text-ink-faint transition-transform ${open ? "-translate-y-0.5 rotate-45" : "-rotate-45"}`}
      />
      {children}
    </button>
  );
}
