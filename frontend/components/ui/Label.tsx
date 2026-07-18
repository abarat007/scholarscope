import type { ReactNode } from "react";

/** Monospace, uppercase, wide-tracked metadata label — the system's caption voice. */
export function Label({
  children,
  className = "",
  as: Tag = "span",
}: {
  children: ReactNode;
  className?: string;
  as?: "span" | "div" | "dt" | "h2";
}) {
  return (
    <Tag className={`font-mono text-xs uppercase tracking-widest text-secondary ${className}`}>
      {children}
    </Tag>
  );
}
