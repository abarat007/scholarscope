# ScholarScope

ScholarScope is a Retrieval-Augmented Generation (RAG) platform. It helps you find and understand research papers on a topic.

## What ScholarScope Does

1. You enter a research topic.
2. ScholarScope gets candidate papers from arXiv.
3. ScholarScope searches the papers with 2 methods: BM25 keyword search and dense vector search. ScholarScope combines the results with Reciprocal Rank Fusion (RRF).
4. A cross-encoder model reranks the top results.
5. ScholarScope reads each paper. It extracts structured data with a Large Language Model (LLM).
6. ScholarScope groups the papers into clusters. It finds the relationships, tensions, and open problems between the clusters.
7. ScholarScope shows the result as an interactive reading map. The map grows as you explore more topics.

## Status

The pipeline works end to end. This includes:

- Ingestion of new papers
- Hybrid retrieval and reranking
- Structured extraction and LLM synthesis
- A LangGraph agent with safety guardrails
- A Redis cache
- Langfuse tracing
- A Next.js frontend

Retrieval and the guardrails do not need an API key. Landscape synthesis needs a funded `ANTHROPIC_API_KEY`.

Evaluation (RAGAS and retrieval metrics) is not complete yet. See [DEMO.md](DEMO.md) for a demo guide.

## Architecture

```
arXiv API → Airflow ingestion → Postgres + OpenSearch (BM25 + k-NN)
    → hybrid retrieval (RRF) → cross-encoder reranking
    → structured extraction (Claude, Pydantic schemas) → landscape synthesis
    → FastAPI + LangGraph (guardrails, Redis caching, Langfuse tracing)
    → Next.js reading map
```

## How to Run ScholarScope

Do these steps in order.

1. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
2. Add your `ANTHROPIC_API_KEY` to `.env`. This step is optional. You need it only for landscape synthesis.
3. Start the stack:
   ```bash
   make start
   ```
4. Check that all services are healthy:
   ```bash
   make health
   ```
5. Start the frontend:
   ```bash
   make frontend
   ```
   The frontend runs at http://localhost:3100.

## Stack

| Layer | Choice |
|---|---|
| Backend API | FastAPI (Python 3.11 or later) |
| Agent orchestration | LangGraph |
| Ingestion scheduler | Apache Airflow |
| Search | OpenSearch (BM25 and k-NN dense vectors) |
| Fusion | Reciprocal Rank Fusion (RRF), written by hand |
| Reranker | Cross-encoder model (`ms-marco-MiniLM-L-6-v2`) |
| LLM | Claude (Sonnet 5), through a provider-agnostic wrapper |
| Metadata store | PostgreSQL |
| Cache | Redis (semantic cache and exact cache) |
| Observability | Langfuse |
| Evaluation | RAGAS, precision@k, and MRR |
| Frontend | Next.js, Tailwind, and react-flow |

## Design Lineage

The architecture is based on 2 sources:

- [`jamwithai/production-agentic-rag-course`](https://github.com/jamwithai/production-agentic-rag-course) — infrastructure and retrieval patterns
- The ResearchPilot paper ([arXiv 2603.14629](https://arxiv.org/abs/2603.14629)) — the extraction and synthesis pipeline

This project is not a fork of either source. It combines ideas from both and adds new features. All code in this repository is new.
