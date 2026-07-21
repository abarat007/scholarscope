const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SearchMode = "bm25" | "dense" | "hybrid";

export interface SearchHit {
  arxiv_id: string;
  title: string;
  abstract: string;
  primary_category: string;
  published_at: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  reranked: boolean | null;
  took_ms: number;
  hits: SearchHit[];
}

export interface BuildResult {
  topic: string;
  version: number;
  papers: number;
  new_papers: number;
  clusters: number;
  rebuilt: boolean;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface GraphNode {
  id: string;
  type: "cluster" | "paper";
  label: string;
  cluster_id: number | null;
  added_in_version: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "membership" | "relationship";
  label: string | null;
}

export interface LandscapeGraph {
  topic: string;
  version: number;
  paper_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  tensions: string[];
  open_problems: string[];
}

export interface PaperExtraction {
  problem: string;
  method: string;
  results: string;
  contribution: string;
  limitations: string;
  key_terms: string[];
}

export interface PaperCard {
  arxiv_id: string;
  title: string;
  extraction: PaperExtraction | null;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function search(
  q: string,
  mode: SearchMode,
  opts: { k?: number; rerank?: boolean; optimize?: boolean } = {},
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, k: String(opts.k ?? 10) });
  if (mode === "hybrid") params.set("rerank", String(opts.rerank ?? true));
  if (opts.optimize) params.set("optimize", "true");
  return request<SearchResponse>(`/search/${mode}?${params.toString()}`);
}

export function buildLandscape(topic: string, papers = 30): Promise<BuildResult> {
  return request<BuildResult>(
    `/landscape/${encodeURIComponent(topic)}/build?papers=${papers}`,
    { method: "POST" },
  );
}

export function getLandscape(topic: string): Promise<LandscapeGraph> {
  return request<LandscapeGraph>(`/landscape/${encodeURIComponent(topic)}`);
}

export function getPaper(arxivId: string): Promise<PaperCard> {
  return request<PaperCard>(`/papers/${arxivId}`);
}

export const arxivAbsUrl = (id: string) => `https://arxiv.org/abs/${id}`;
