"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function TopicBar({ initial = "" }: { initial?: string }) {
  const router = useRouter();
  const [value, setValue] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) router.push(`/?q=${encodeURIComponent(q)}`);
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Enter a research topic, e.g. retrieval augmented generation"
        className="flex-1 rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />
      <button
        type="submit"
        className="rounded-lg bg-accent px-5 py-3 font-medium text-ink-950 hover:bg-accent-soft transition-colors"
      >
        Explore
      </button>
    </form>
  );
}
