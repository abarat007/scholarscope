import BuildLandscapeButton from "@/components/BuildLandscapeButton";
import SearchResults from "@/components/SearchResults";
import TopicBar from "@/components/TopicBar";
import TopicHistory from "@/components/TopicHistory";

export default function Home({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const query = searchParams.q?.trim() ?? "";

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        {!query && (
          <div className="text-center py-8">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-100">
              Map the research landscape of any topic
            </h1>
            <p className="text-slate-400 mt-2 max-w-xl mx-auto">
              Hybrid retrieval over a live arXiv corpus, cross-encoder reranking, and
              LLM-synthesized clusters — rendered as a reading map that grows as you explore.
            </p>
          </div>
        )}
        <TopicBar initial={query} />
      </section>

      {query ? (
        <>
          <BuildLandscapeButton topic={query} />
          <section>
            <h2 className="text-sm font-medium text-slate-400 mb-3">
              Retrieved papers for <span className="text-accent-soft">{query}</span>
            </h2>
            <SearchResults query={query} />
          </section>
        </>
      ) : (
        <TopicHistory />
      )}
    </div>
  );
}
