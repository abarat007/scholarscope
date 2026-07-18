"use client";

import { useCallback, useEffect, useState } from "react";
import { search, arxivAbsUrl, ApiError, type SearchHit, type SearchMode } from "@/lib/api";

const MODES: { key: SearchMode; label: string }[] = [
  { key: "hybrid", label: "Hybrid + Rerank" },
  { key: "bm25", label: "BM25 keyword" },
  { key: "dense", label: "Dense vector" },
];

export default function SearchResults({ query }: { query: string }) {
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [rerank, setRerank] = useState(true);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [tookMs, setTookMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (nextMode: SearchMode, nextRerank: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const res = await search(query, nextMode, { k: 10, rerank: nextRerank });
        setHits(res.hits);
        setTookMs(res.took_ms);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Search failed. Is the backend running?");
        setHits([]);
      } finally {
        setLoading(false);
      }
    },
    [query],
  );

  // Re-run whenever the query changes (mode/rerank changes call run() directly).
  useEffect(() => {
    run(mode, rerank);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => {
              setMode(m.key);
              run(m.key, rerank);
            }}
            className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
              mode === m.key
                ? "border-accent bg-accent/15 text-accent-soft"
                : "border-ink-700 text-slate-400 hover:border-ink-600"
            }`}
          >
            {m.label}
          </button>
        ))}
        {mode === "hybrid" && (
          <label className="flex items-center gap-2 text-sm text-slate-400 ml-1">
            <input
              type="checkbox"
              checked={rerank}
              onChange={(e) => {
                setRerank(e.target.checked);
                run("hybrid", e.target.checked);
              }}
              className="accent-accent"
            />
            reranker
          </label>
        )}
        {tookMs !== null && !loading && (
          <span className="text-xs text-slate-500 ml-auto font-mono">{tookMs.toFixed(0)} ms</span>
        )}
      </div>

      {loading && <SkeletonList />}

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && hits.length === 0 && (
        <p className="text-slate-500 text-sm py-8 text-center">
          No papers matched. Try a broader topic.
        </p>
      )}

      {!loading &&
        hits.map((hit, i) => (
          <a
            key={hit.arxiv_id}
            href={arxivAbsUrl(hit.arxiv_id)}
            target="_blank"
            rel="noreferrer"
            className="block rounded-lg border border-ink-800 bg-ink-900/40 px-4 py-3 hover:border-accent-dim transition-colors animate-fade-in"
            style={{ animationDelay: `${i * 20}ms` }}
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="font-medium text-slate-100 leading-snug">{hit.title}</h3>
              <span className="text-xs font-mono text-slate-500 shrink-0 mt-0.5">
                {hit.score.toFixed(3)}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1.5 line-clamp-2">{hit.abstract}</p>
            <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
              <span className="px-1.5 py-0.5 rounded bg-ink-800 text-accent-soft">
                {hit.primary_category}
              </span>
              <span className="font-mono">{hit.arxiv_id}</span>
              <span>{new Date(hit.published_at).toLocaleDateString()}</span>
            </div>
          </a>
        ))}
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-ink-800 bg-ink-900/40 px-4 py-3">
          <div className="h-4 bg-ink-700 rounded w-3/4 animate-pulse" />
          <div className="h-3 bg-ink-800 rounded w-full mt-2.5 animate-pulse" />
          <div className="h-3 bg-ink-800 rounded w-5/6 mt-1.5 animate-pulse" />
        </div>
      ))}
    </div>
  );
}
