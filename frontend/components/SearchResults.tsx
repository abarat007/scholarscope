"use client";

import { useCallback, useEffect, useState } from "react";
import { search, arxivAbsUrl, ApiError, type SearchHit, type SearchMode } from "@/lib/api";

const MODES: { key: SearchMode; label: string }[] = [
  { key: "hybrid", label: "Hybrid + Rerank" },
  { key: "bm25", label: "BM25 Keyword" },
  { key: "dense", label: "Dense Vector" },
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

  useEffect(() => {
    run(mode, rerank);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div>
      {/* Mode selector — underlined editorial tabs, not buttons. */}
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
        <div className="flex flex-wrap gap-6">
          {MODES.map((m) => {
            const active = mode === m.key;
            return (
              <button
                key={m.key}
                onClick={() => {
                  setMode(m.key);
                  run(m.key, rerank);
                }}
                className={`font-mono text-xs uppercase tracking-widest transition-none focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:outline-offset-2 ${
                  active
                    ? "border-b-2 border-foreground pb-1 text-foreground"
                    : "border-b-2 border-transparent pb-1 text-secondary hover:text-foreground"
                }`}
              >
                {m.label}
              </button>
            );
          })}
          {mode === "hybrid" && (
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs uppercase tracking-widest text-secondary">
              <input
                type="checkbox"
                checked={rerank}
                onChange={(e) => {
                  setRerank(e.target.checked);
                  run("hybrid", e.target.checked);
                }}
                className="h-3.5 w-3.5 appearance-none border-2 border-foreground bg-background checked:bg-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-foreground focus-visible:outline-offset-2"
              />
              Rerank
            </label>
          )}
        </div>
        {tookMs !== null && !loading && (
          <span className="font-mono text-xs uppercase tracking-widest text-secondary">
            {tookMs.toFixed(0)} ms
          </span>
        )}
      </div>

      {loading && <SkeletonList />}

      {error && (
        <div className="invert-panel px-6 py-5">
          <p className="font-mono text-xs uppercase tracking-widest">Error</p>
          <p className="mt-2 font-serif text-lg">{error}</p>
        </div>
      )}

      {!loading && !error && hits.length === 0 && (
        <p className="py-16 text-center font-display text-2xl italic text-secondary">
          No papers matched. Try a broader topic.
        </p>
      )}

      {!loading && (
        <ol>
          {hits.map((hit, i) => (
            <li key={hit.arxiv_id}>
              <a
                href={arxivAbsUrl(hit.arxiv_id)}
                target="_blank"
                rel="noreferrer"
                className="group grid grid-cols-[auto_1fr_auto] items-start gap-x-5 gap-y-2 border-b border-line px-2 py-5 transition-colors duration-100 hover:bg-foreground hover:text-background focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:-outline-offset-[3px]"
              >
                <span className="font-mono text-sm tabular-nums text-secondary group-hover:text-background">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="font-display text-xl leading-snug md:text-2xl">{hit.title}</h3>
                  <p className="mt-1.5 line-clamp-2 font-serif text-base text-secondary group-hover:text-background/80">
                    {hit.abstract}
                  </p>
                  <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs uppercase tracking-widest text-secondary group-hover:text-background/70">
                    <span className="border border-current px-1.5 py-0.5">{hit.primary_category}</span>
                    <span>{hit.arxiv_id}</span>
                    <span>{new Date(hit.published_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <span className="self-center font-mono text-sm tabular-nums text-secondary group-hover:text-background">
                  {hit.score.toFixed(3)}
                </span>
              </a>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function SkeletonList() {
  return (
    <div>
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="grid grid-cols-[auto_1fr] gap-5 border-b border-line px-2 py-5">
          <div className="h-4 w-6 bg-subtle" />
          <div className="space-y-2.5">
            <div className="h-5 w-3/4 bg-subtle" />
            <div className="h-3 w-full bg-subtle" />
            <div className="h-3 w-5/6 bg-subtle" />
          </div>
        </div>
      ))}
    </div>
  );
}
