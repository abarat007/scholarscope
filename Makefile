PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

QUERY ?= cat:cs.CL
MAX ?= 2000

.PHONY: start stop health test test-integration lint eval logs backfill frontend reindex demo-landscapes

start:
	docker compose up -d --build

stop:
	docker compose down

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool

test:
	cd backend && ../$(PYTHON) -m pytest -q

test-integration:
	cd backend && POSTGRES_PORT=$${POSTGRES_PORT:-5433} ../$(PYTHON) -m pytest -q -m integration --override-ini "addopts="

backfill:
	docker compose exec backend python -m src.services.ingestion.backfill --query '$(QUERY)' --max-papers $(MAX)

reindex:
	docker compose exec backend python -m src.services.retrieval.reindex

frontend:
	# Pinned to 3100: 3000 is Langfuse, 3001 may be another local project.
	cd frontend && npm install && npm run dev -- -p 3100

# Build a few landscapes for a demo (requires ANTHROPIC_API_KEY with credits).
demo-landscapes:
	@for t in "retrieval augmented generation" "cross-encoder reranking" "llm agents"; do \
		echo "building: $$t"; \
		curl -s -X POST "http://localhost:8000/landscape/$$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$$t")/build?papers=30" | python3 -m json.tool; \
	done

lint:
	cd backend && ../$(RUFF) check src tests

eval:
	@echo "Evaluation suite lands in Phase 6: retrieval metrics (precision@k, MRR) + RAGAS."
	@exit 1

logs:
	docker compose logs -f --tail=100
