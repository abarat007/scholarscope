"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { buildLandscape, ApiError } from "@/lib/api";
import { recordVisit } from "@/lib/history";

export default function BuildLandscapeButton({ topic }: { topic: string }) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "building" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function build() {
    setStatus("building");
    setMessage(null);
    try {
      const result = await buildLandscape(topic, 30);
      recordVisit(result.topic, result.papers);
      router.push(`/landscape/${encodeURIComponent(result.topic)}`);
    } catch (e) {
      setStatus("error");
      if (e instanceof ApiError && e.status === 503) {
        setMessage("The LLM provider is unavailable (check API credits). Retrieval still works above.");
      } else if (e instanceof ApiError && e.status === 400) {
        setMessage(typeof e.detail === "object" ? "Query blocked by input guardrails." : e.message);
      } else {
        setMessage("Landscape build failed. Is the backend running with an API key?");
      }
    }
  }

  return (
    <div className="rounded-lg border border-accent-dim/40 bg-accent/5 px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-200">Synthesize a research landscape for this topic</p>
          <p className="text-xs text-slate-500 mt-0.5">
            Extracts each paper, clusters them, and maps relationships, tensions & open problems.
          </p>
        </div>
        <button
          onClick={build}
          disabled={status === "building"}
          className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink-950 hover:bg-accent-soft transition-colors disabled:opacity-60"
        >
          {status === "building" ? "Building…" : "Build map"}
        </button>
      </div>
      {status === "building" && (
        <p className="text-xs text-slate-400 mt-2 animate-pulse">
          Extracting papers and synthesizing clusters — this can take a minute…
        </p>
      )}
      {message && <p className="text-xs text-amber-300/90 mt-2">{message}</p>}
    </div>
  );
}
