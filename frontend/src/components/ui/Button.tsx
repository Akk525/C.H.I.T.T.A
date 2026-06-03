import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--chitta-accent)] text-white shadow-sm hover:bg-[var(--chitta-accent-hover)]",
  secondary:
    "border border-[var(--chitta-border)] bg-[var(--chitta-surface)] text-[var(--chitta-ink)] shadow-sm hover:bg-[var(--chitta-bg)]",
  ghost: "text-[var(--chitta-muted)] hover:bg-[var(--chitta-accent-soft)] hover:text-[var(--chitta-accent)]",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  href?: string;
  children: ReactNode;
  className?: string;
};

export function Button({
  variant = "primary",
  href,
  children,
  className = "",
  ...rest
}: Props) {
  const base =
    "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const classes = `${base} ${VARIANTS[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  );
}
