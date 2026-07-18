"use client";

import { useEffect, useState } from "react";
import { getPaper, arxivAbsUrl, type PaperCard as PaperCardData } from "@/lib/api";

export default function PaperCard({
  arxivId,
  onClose,
}: {
  arxivId: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<PaperCardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getPaper(arxivId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [arxivId]);

  return (
    <div className="absolute top-0 right-0 h-full w-full max-w-md border-l border-ink-800 bg-ink-900/95 backdrop-blur p-5 overflow-y-auto z-10 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-xs text-slate-500">{arxivId}</span>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-200 text-lg leading-none">
          ✕
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500 mt-4 animate-pulse">Loading…</p>}

      {!loading && data && (
        <div className="mt-2 space-y-4">
          <h3 className="font-medium text-slate-100 leading-snug">{data.title}</h3>
          <a
            href={arxivAbsUrl(arxivId)}
            target="_blank"
            rel="noreferrer"
            className="inline-block text-xs text-accent hover:text-accent-soft"
          >
            View on arXiv →
          </a>

          {data.extraction ? (
            <dl className="space-y-3">
              <Field label="Problem" value={data.extraction.problem} />
              <Field label="Method" value={data.extraction.method} />
              <Field label="Results" value={data.extraction.results} />
              <Field label="Contribution" value={data.extraction.contribution} />
              <Field label="Limitations" value={data.extraction.limitations} />
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500 mb-1">Key terms</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {data.extraction.key_terms.map((t) => (
                    <span key={t} className="px-2 py-0.5 rounded bg-ink-800 text-xs text-accent-soft">
                      {t}
                    </span>
                  ))}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-500">
              No structured extraction cached yet — build the landscape to generate one.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500 mb-0.5">{label}</dt>
      <dd className="text-sm text-slate-300 leading-relaxed">{value}</dd>
    </div>
  );
}
