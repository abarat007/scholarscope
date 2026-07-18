"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getLandscape, buildLandscape, ApiError, type LandscapeGraph } from "@/lib/api";
import { priorPaperCount, recordVisit } from "@/lib/history";
import ReadingMap from "@/components/ReadingMap";

export default function LandscapeView({ topic }: { topic: string }) {
  const [graph, setGraph] = useState<LandscapeGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [growth, setGrowth] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const prior = priorPaperCount(topic);
    getLandscape(topic)
      .then((g) => {
        setGraph(g);
        if (prior !== null && g.paper_count > prior) setGrowth(g.paper_count - prior);
        recordVisit(g.topic, g.paper_count);
      })
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? "not_found" : "error"))
      .finally(() => setLoading(false));
  }, [topic]);

  async function refresh() {
    setRefreshing(true);
    try {
      await buildLandscape(topic, 30);
      const g = await getLandscape(topic);
      const prior = graph?.paper_count ?? 0;
      setGraph(g);
      if (g.paper_count > prior) setGrowth(g.paper_count - prior);
      recordVisit(g.topic, g.paper_count);
    } catch {
      /* keep the current view; refresh is best-effort */
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return <p className="text-slate-500 animate-pulse py-16 text-center">Loading landscape…</p>;
  }

  if (error === "not_found") {
    return (
      <div className="py-16 text-center space-y-3">
        <p className="text-slate-400">No landscape has been built for “{topic}” yet.</p>
        <Link href={`/?q=${encodeURIComponent(topic)}`} className="text-accent hover:text-accent-soft">
          ← Explore this topic and build one
        </Link>
      </div>
    );
  }

  if (error || !graph) {
    return <p className="text-red-300 py-16 text-center">Failed to load. Is the backend running?</p>;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
            <Link href="/" className="hover:text-accent-soft">
              ← All topics
            </Link>
          </div>
          <h1 className="text-2xl font-semibold text-slate-100">{graph.topic}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {graph.paper_count} papers · {graph.nodes.filter((n) => n.type === "cluster").length}{" "}
            clusters · version {graph.version}
            {growth !== null && (
              <span className="ml-2 text-emerald-400">+{growth} new since your last visit</span>
            )}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="shrink-0 rounded-lg border border-ink-700 px-3 py-2 text-sm text-slate-300 hover:border-accent-dim transition-colors disabled:opacity-60"
        >
          {refreshing ? "Growing…" : "Grow map"}
        </button>
      </div>

      <ReadingMap graph={graph} latestVersion={graph.version} />

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Tensions" items={graph.tensions} accent="amber" />
        <Panel title="Open problems" items={graph.open_problems} accent="accent" />
      </div>
    </div>
  );
}

function Panel({
  title,
  items,
  accent,
}: {
  title: string;
  items: string[];
  accent: "amber" | "accent";
}) {
  const dot = accent === "amber" ? "text-amber-400" : "text-accent";
  return (
    <div className="rounded-lg border border-ink-800 bg-ink-900/40 p-4">
      <h2 className="text-sm font-medium text-slate-300 mb-2">{title}</h2>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600">None surfaced.</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-slate-400 flex gap-2">
              <span className={dot}>•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
