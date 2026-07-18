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
    <div className="absolute right-0 top-0 z-10 h-full w-full max-w-md overflow-y-auto border-l-2 border-foreground bg-background p-6 animate-fade-up">
      <div className="flex items-start justify-between gap-3 border-b border-line pb-3">
        <span className="font-mono text-xs uppercase tracking-widest text-secondary">{arxivId}</span>
        <button
          onClick={onClose}
          aria-label="Close"
          className="font-mono text-sm leading-none text-foreground hover:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-foreground focus-visible:outline-offset-2"
        >
          ✕
        </button>
      </div>

      {loading && (
        <p className="mt-6 font-mono text-xs uppercase tracking-widest text-secondary">Loading…</p>
      )}

      {!loading && data && (
        <div className="mt-4 space-y-5">
          <h3 className="font-display text-2xl leading-snug">{data.title}</h3>
          <a
            href={arxivAbsUrl(arxivId)}
            target="_blank"
            rel="noreferrer"
            className="inline-block font-mono text-xs uppercase tracking-widest underline decoration-transparent underline-offset-4 hover:decoration-foreground"
          >
            View on arXiv →
          </a>

          {data.extraction ? (
            <dl className="divide-y divide-line border-t border-line">
              <Field label="Problem" value={data.extraction.problem} />
              <Field label="Method" value={data.extraction.method} />
              <Field label="Results" value={data.extraction.results} />
              <Field label="Contribution" value={data.extraction.contribution} />
              <Field label="Limitations" value={data.extraction.limitations} />
              <div className="py-4">
                <dt className="mb-2 font-mono text-xs uppercase tracking-widest text-secondary">
                  Key terms
                </dt>
                <dd className="flex flex-wrap gap-1.5">
                  {data.extraction.key_terms.map((t) => (
                    <span
                      key={t}
                      className="border border-foreground px-2 py-0.5 font-mono text-xs"
                    >
                      {t}
                    </span>
                  ))}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="border-t border-line pt-4 font-serif text-base italic text-secondary">
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
    <div className="py-4">
      <dt className="mb-1 font-mono text-xs uppercase tracking-widest text-secondary">{label}</dt>
      <dd className="font-serif text-base leading-relaxed text-foreground">{value}</dd>
    </div>
  );
}
