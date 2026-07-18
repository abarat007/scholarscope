import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

type Variant = "primary" | "outline" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 font-mono text-xs font-medium uppercase tracking-widest transition-colors duration-100 focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:outline-offset-[3px] disabled:opacity-40 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  // Black field, inverts to outlined-white on hover.
  primary:
    "bg-foreground text-background px-8 py-4 border-2 border-foreground hover:bg-background hover:text-foreground",
  // Outlined, fills black on hover.
  outline:
    "bg-transparent text-foreground px-8 py-4 border-2 border-foreground hover:bg-foreground hover:text-background",
  // Text link with an underline on hover.
  ghost:
    "bg-transparent text-foreground px-1 py-1 border-0 underline decoration-transparent underline-offset-4 hover:decoration-foreground",
};

interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  variant?: Variant;
  children: ReactNode;
}

export function Button({ variant = "primary", className = "", children, ...props }: ButtonProps) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

interface ButtonLinkProps {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}

export function ButtonLink({ href, variant = "primary", className = "", children }: ButtonLinkProps) {
  return (
    <Link href={href} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  );
}
