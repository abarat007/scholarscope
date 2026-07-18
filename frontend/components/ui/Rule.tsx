type Weight = "hairline" | "thin" | "thick" | "ultra";

const weights: Record<Weight, string> = {
  hairline: "border-t border-line",
  thin: "border-t border-foreground",
  thick: "border-t-4 border-foreground",
  ultra: "border-t-8 border-foreground",
};

/** A horizontal rule — the primary structural divider of the system. */
export function Rule({ weight = "thick", className = "" }: { weight?: Weight; className?: string }) {
  return <hr className={`${weights[weight]} ${className}`} />;
}

/**
 * The signature section punctuation: a thick rule interrupted by a small
 * bordered square. Used to open major sections.
 */
export function RuleMark({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <span className="h-3 w-3 border-2 border-foreground bg-background" aria-hidden />
      <span className="h-1 flex-1 bg-foreground" aria-hidden />
    </div>
  );
}
