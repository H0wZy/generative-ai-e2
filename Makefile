.PHONY: help up down migrate migrate-test test test-unit ingest-demo worker-once clean

BACKEND_DIR := backend
DB_URL      ?= postgresql://genai_e2:genai_e2_dev@localhost:5432/genai_e2
TEST_DB_URL ?= postgresql://genai_e2:genai_e2_dev@localhost:5432/genai_e2_test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ─── Infrastructure ─────────────────────────────────────────────────────────

up: ## Start PostgreSQL dev database (port 5432 via Docker)
	docker compose up -d postgres
	@echo "Waiting for PostgreSQL..."
	@until docker compose exec postgres pg_isready -U genai_e2 -d genai_e2 > /dev/null 2>&1; do sleep 1; done
	@echo "PostgreSQL is ready."
	@docker compose exec postgres psql -U genai_e2 -d genai_e2 \
	  -tc "SELECT 1 FROM pg_database WHERE datname='genai_e2_test'" | grep -q 1 \
	  || docker compose exec postgres psql -U genai_e2 -d genai_e2 \
	     -c "CREATE DATABASE genai_e2_test OWNER genai_e2;" && echo "Test database created."

down: ## Stop all containers
	docker compose down

## ─── Migrations ─────────────────────────────────────────────────────────────

migrate: ## Apply Alembic migrations to dev database
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) python -m alembic upgrade head

migrate-test: ## Apply Alembic migrations to test database
	cd $(BACKEND_DIR) && DATABASE_URL=$(TEST_DB_URL) python -m alembic upgrade head

## ─── Tests ───────────────────────────────────────────────────────────────────

test: ## Run full test suite
	cd $(BACKEND_DIR) && TEST_DATABASE_URL=$(TEST_DB_URL) python -m pytest -v

test-unit: ## Run unit tests only (no DB required)
	cd $(BACKEND_DIR) && python -m pytest tests/test_jira_client.py -v

## ─── Demo ────────────────────────────────────────────────────────────────────

ingest-demo: ## POST the synthetic fixture to the local API (requires make up + migrate + uvicorn)
	@echo "Ingesting synthetic Freshservice ticket..."
	curl -s -X POST http://localhost:8000/api/v1/tickets/ingest \
	  -H "Content-Type: application/json" \
	  -d @$(BACKEND_DIR)/tests/fixtures/ticket_created.json | python3 -m json.tool

worker-once: ## Claim and process one outbox event
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) python -m app.worker --once

## ─── Maintenance ──────────────────────────────────────────────────────────────

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
