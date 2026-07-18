"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getLandscape, buildLandscape, ApiError, type LandscapeGraph } from "@/lib/api";
import { priorPaperCount, recordVisit } from "@/lib/history";
import ReadingMap from "@/components/ReadingMap";
import { Label } from "@/components/ui/Label";
import { Rule } from "@/components/ui/Rule";

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
      /* best-effort */
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return (
      <p className="py-24 text-center font-display text-3xl italic text-secondary">
        Loading landscape…
      </p>
    );
  }

  if (error === "not_found") {
    return (
      <div className="space-y-6 py-16">
        <Label>Not found</Label>
        <p className="font-display text-4xl italic md:text-5xl">
          No landscape for “{topic}” yet.
        </p>
        <Link
          href={`/?q=${encodeURIComponent(topic)}`}
          className="inline-block font-mono text-xs uppercase tracking-widest underline decoration-transparent underline-offset-4 hover:decoration-foreground"
        >
          ← Explore this topic and build one
        </Link>
      </div>
    );
  }

  if (error || !graph) {
    return (
      <p className="py-24 text-center font-display text-2xl italic text-secondary">
        Failed to load. Is the backend running?
      </p>
    );
  }

  const clusterCount = graph.nodes.filter((n) => n.type === "cluster").length;

  return (
    <div className="space-y-10">
      <div>
        <Link
          href="/"
          className="font-mono text-xs uppercase tracking-widest text-secondary underline decoration-transparent underline-offset-4 hover:text-foreground hover:decoration-foreground"
        >
          ← All topics
        </Link>
        <div className="mt-6 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-display text-4xl font-black leading-none tracking-tighter md:text-6xl">
              {graph.topic}
            </h1>
            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 font-mono text-xs uppercase tracking-widest text-secondary">
              <span>{graph.paper_count} papers</span>
              <span>{clusterCount} clusters</span>
              <span>Version {graph.version}</span>
              {growth !== null && (
                <span className="invert-panel px-2 py-1">+{growth} new since last visit</span>
              )}
            </div>
          </div>
          <button
            onClick={refresh}
            disabled={refreshing}
            className="shrink-0 border-2 border-foreground bg-transparent px-6 py-3 font-mono text-xs font-medium uppercase tracking-widest text-foreground transition-colors duration-100 hover:bg-foreground hover:text-background focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:outline-offset-[3px] disabled:opacity-50"
          >
            {refreshing ? "Growing…" : "Grow map →"}
          </button>
        </div>
      </div>

      <Rule weight="thick" />

      <ReadingMap graph={graph} latestVersion={graph.version} />

      <div className="grid gap-px border border-line bg-line md:grid-cols-2">
        <QuotePanel title="Tensions" items={graph.tensions} />
        <QuotePanel title="Open Problems" items={graph.open_problems} />
      </div>
    </div>
  );
}

function QuotePanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="bg-background p-8">
      <Label as="h2" className="mb-6 block">
        {title}
      </Label>
      {items.length === 0 ? (
        <p className="font-serif text-base italic text-secondary">None surfaced.</p>
      ) : (
        <ul className="space-y-6">
          {items.map((item, i) => (
            <li key={i} className="relative pl-10">
              <span
                aria-hidden
                className="absolute left-0 top-0 font-display text-5xl italic leading-none text-foreground"
              >
                “
              </span>
              <p className="font-serif text-lg leading-relaxed">{item}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
