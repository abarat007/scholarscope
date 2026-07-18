"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { loadHistory, type TopicVisit } from "@/lib/history";

export default function TopicHistory() {
  const [history, setHistory] = useState<TopicVisit[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  if (history.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-sm font-medium text-slate-400 mb-3">Your reading map</h2>
      <div className="flex flex-wrap gap-2">
        {history.map((v) => (
          <Link
            key={v.topic}
            href={`/landscape/${encodeURIComponent(v.topic)}`}
            className="group rounded-lg border border-ink-800 bg-ink-900/40 px-3 py-2 hover:border-accent-dim transition-colors"
          >
            <span className="text-sm text-slate-200 group-hover:text-accent-soft">
              {v.topic}
            </span>
            <span className="block text-xs text-slate-500 mt-0.5">
              {v.lastPaperCount} papers · {new Date(v.visitedAt).toLocaleDateString()}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
