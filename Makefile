PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

QUERY ?= cat:cs.CL
MAX ?= 2000

.PHONY: start stop health test test-integration lint eval logs backfill

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

lint:
	cd backend && ../$(RUFF) check src tests

eval:
	@echo "Evaluation suite lands in Phase 6: retrieval metrics (precision@k, MRR) + RAGAS."
	@exit 1

logs:
	docker compose logs -f --tail=100
