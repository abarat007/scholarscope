# ScholarScope

**A production-style RAG platform for research landscape discovery.**

Enter a research topic; ScholarScope pulls candidate papers from arXiv, retrieves
with hybrid search (BM25 + dense embeddings fused via hand-written RRF), reranks
with a cross-encoder, runs structured per-paper extraction with LLM structured
outputs, and synthesizes a cross-paper research landscape — clusters,
relationships, tensions, and open problems — rendered as an interactive reading
map that grows as you explore more topics.

> **Status:** Phase 1 — infrastructure skeleton. See the build phases below.

## Architecture

*Architecture diagram coming soon.*

```
arXiv API → Airflow ingestion → Postgres + OpenSearch (BM25 + k-NN)
    → hybrid retrieval (RRF) → cross-encoder reranking
    → structured extraction (Claude, Pydantic schemas) → landscape synthesis
    → FastAPI + LangGraph (guardrails, Redis caching, Langfuse tracing)
    → Next.js reading map
```

## Stack

| Layer | Choice |
|---|---|
| Backend API | FastAPI (Python 3.11+) |
| Orchestration | LangGraph |
| Ingestion scheduler | Apache Airflow |
| Search | OpenSearch (BM25 + k-NN dense vectors) |
| Fusion | Reciprocal Rank Fusion (implemented by hand) |
| Reranker | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) |
| LLM | Claude (Sonnet 5) via a provider-agnostic wrapper |
| Metadata | PostgreSQL |
| Cache | Redis (semantic + exact) |
| Observability | Langfuse |
| Evaluation | RAGAS + precision@k / MRR |
| Frontend | Next.js + Tailwind + react-flow |

## Quickstart

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY
make start             # bring up the full stack
make health            # check every dependency
```

## Design lineage

Architecture informed by
[`jamwithai/production-agentic-rag-course`](https://github.com/jamwithai/production-agentic-rag-course)
(infra/retrieval patterns) and the ResearchPilot paper
([arXiv 2603.14629](https://arxiv.org/abs/2603.14629))
(extraction/synthesis pipeline). This project merges, reimplements, and extends
both — it is not a fork; all code here is written fresh.
