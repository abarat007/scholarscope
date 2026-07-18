import BuildLandscapeButton from "@/components/BuildLandscapeButton";
import SearchResults from "@/components/SearchResults";
import TopicBar from "@/components/TopicBar";
import TopicHistory from "@/components/TopicHistory";
import { Label } from "@/components/ui/Label";
import { Rule, RuleMark } from "@/components/ui/Rule";

export default function Home({ searchParams }: { searchParams: { q?: string } }) {
  const query = searchParams.q?.trim() ?? "";

  return (
    <div>
      {!query && (
        <section className="pb-8">
          <Label className="mb-4 block">Est. arXiv · cs.CL / cs.AI / cs.LG</Label>
          <h1 className="font-display font-black leading-none tracking-tighter">
            <span className="block text-3xl md:text-4xl lg:text-5xl">Map the</span>
            <span className="block text-4xl italic md:text-5xl lg:text-6xl">research</span>
            <span className="block text-3xl md:text-4xl lg:text-5xl">landscape.</span>
          </h1>
          <div className="mt-6 grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
            <p className="max-w-xl font-serif text-base text-secondary md:text-lg">
              Hybrid retrieval over a live corpus, cross-encoder reranking, and
              LLM-synthesized clusters — rendered as a reading map that grows as you explore.
            </p>
            <Label className="hidden md:block md:text-right">
              Enter a topic below
              <br />
              to begin ↓
            </Label>
          </div>
          <RuleMark className="mt-6" />
        </section>
      )}

      <section className={query ? "" : "pt-2"}>
        <TopicBar initial={query} />
      </section>

      {query ? (
        <div className="mt-12 space-y-12">
          <BuildLandscapeButton topic={query} />

          <section>
            <div className="mb-6 flex items-baseline justify-between gap-4">
              <Label as="h2">Retrieved papers</Label>
              <span className="truncate font-display text-2xl italic md:text-3xl">{query}</span>
            </div>
            <Rule weight="thin" className="mb-6" />
            <SearchResults query={query} />
          </section>
        </div>
      ) : (
        <div className="mt-16">
          <TopicHistory />
        </div>
      )}
    </div>
  );
}
