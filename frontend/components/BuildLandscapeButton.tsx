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
        setMessage("LLM provider unavailable — check API credits. Retrieval below still works.");
      } else if (e instanceof ApiError && e.status === 400) {
        setMessage("Query blocked by input guardrails.");
      } else {
        setMessage("Landscape build failed. Is the backend running with an API key?");
      }
    }
  }

  return (
    <section className="invert-panel px-6 py-8 md:px-10 md:py-10">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-widest text-background/60">Synthesis</p>
          <h2 className="mt-2 font-display text-3xl leading-tight md:text-4xl">
            Build the research landscape.
          </h2>
          <p className="mt-3 font-serif text-base text-background/80 md:text-lg">
            Extract every paper, cluster them, and map the relationships, tensions, and open
            problems across the field.
          </p>
        </div>
        <button
          onClick={build}
          disabled={status === "building"}
          className="group flex shrink-0 items-center justify-center gap-3 border-2 border-background bg-background px-8 py-4 font-mono text-xs font-medium uppercase tracking-widest text-foreground transition-colors duration-100 hover:bg-transparent hover:text-background focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-background focus-visible:outline-offset-[3px] disabled:opacity-50"
        >
          {status === "building" ? "Building…" : "Build map"}
          {status !== "building" && <span aria-hidden>→</span>}
        </button>
      </div>
      {status === "building" && (
        <p className="mt-5 border-t border-background/20 pt-4 font-mono text-xs uppercase tracking-widest text-background/70">
          Extracting papers · clustering · synthesizing — this can take a minute…
        </p>
      )}
      {message && (
        <p className="mt-5 border-t border-background/20 pt-4 font-mono text-xs uppercase tracking-widest text-background/80">
          {message}
        </p>
      )}
    </section>
  );
}
