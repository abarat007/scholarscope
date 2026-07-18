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
    <form onSubmit={submit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <div className="flex-1">
        <label htmlFor="topic" className="mb-2 block font-mono text-xs uppercase tracking-widest text-secondary">
          Research topic
        </label>
        <input
          id="topic"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. retrieval augmented generation"
          className="w-full border-0 border-b-2 border-foreground bg-transparent pb-3 font-serif text-xl text-foreground placeholder:italic placeholder:text-secondary focus:border-b-4 focus:outline-none md:text-2xl"
        />
      </div>
      <button
        type="submit"
        className="group flex items-center justify-center gap-3 border-2 border-foreground bg-foreground px-8 py-4 font-mono text-xs font-medium uppercase tracking-widest text-background transition-colors duration-100 hover:bg-background hover:text-foreground focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-foreground focus-visible:outline-offset-[3px]"
      >
        Explore
        <span aria-hidden>→</span>
      </button>
    </form>
  );
}
