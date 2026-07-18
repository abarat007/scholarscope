"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { loadHistory, type TopicVisit } from "@/lib/history";
import { Label } from "@/components/ui/Label";
import { Rule } from "@/components/ui/Rule";

export default function TopicHistory() {
  const [history, setHistory] = useState<TopicVisit[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  if (history.length === 0) return null;

  return (
    <section>
      <div className="mb-6 flex items-baseline justify-between">
        <Label as="h2">Your reading map</Label>
        <Label>{String(history.length).padStart(2, "0")} topics</Label>
      </div>
      <Rule weight="thin" className="mb-2" />
      <ol>
        {history.map((v, i) => (
          <li key={v.topic}>
            <Link
              href={`/landscape/${encodeURIComponent(v.topic)}`}
              className="group grid grid-cols-[auto_1fr_auto] items-baseline gap-5 border-b border-line py-5 transition-colors duration-100 hover:bg-foreground hover:px-4 hover:text-background focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:-outline-offset-[3px]"
            >
              <span className="font-mono text-sm tabular-nums text-secondary group-hover:text-background">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="font-display text-2xl italic md:text-3xl">{v.topic}</span>
              <span className="font-mono text-xs uppercase tracking-widest text-secondary group-hover:text-background/70">
                {v.lastPaperCount} papers
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
