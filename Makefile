PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

.PHONY: start stop health test lint eval logs

start:
	docker compose up -d --build

stop:
	docker compose down

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool

test:
	cd backend && ../$(PYTHON) -m pytest -q

lint:
	cd backend && ../$(RUFF) check src tests

eval:
	@echo "Evaluation suite lands in Phase 6: retrieval metrics (precision@k, MRR) + RAGAS."
	@exit 1

logs:
	docker compose logs -f --tail=100
