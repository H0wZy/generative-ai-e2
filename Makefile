.PHONY: help up down db-init-local migrate migrate-test test test-unit ingest-demo worker-once clean routing-eval rag-sync rag-eval serve \
        dev dev-down dev-logs venv install install-dev install-rag rag-test api-up frontend spec spec-list spec-current sdd

BACKEND_DIR := backend
VENV        := $(CURDIR)/.venv
SPECIFY     := .specify/scripts/bash/create-new-feature.sh
DB_URL      ?= postgresql://genai_e2:genai_e2_dev@localhost:5432/genai_e2
TEST_DB_URL ?= postgresql://genai_e2:genai_e2_dev@localhost:5432/genai_e2_test

## ─── OS profile (windows/powershell vs linux/bash) ────────────────────────────
## GNU Make on Windows runs recipes via sh.exe (Git Bash), so bash syntax below
## works on both. Only the venv layout and python binary name differ per OS.
ifeq ($(OS),Windows_NT)
  PY         := $(VENV)/Scripts/python.exe
  PYTHON_BIN := python
else
  PY         := $(VENV)/bin/python
  PYTHON_BIN := python3
endif

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ─── Dev environment ────────────────────────────────────────────────────────

dev: up api-up migrate frontend ## One command dev stack: postgres + api container + .venv + migrations + frontend

dev-down: ## Stop the whole dev stack
	docker compose down --remove-orphans

dev-logs: ## Tail api + postgres logs
	docker compose logs -f api postgres

$(PY):
	$(PYTHON_BIN) -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r $(BACKEND_DIR)/requirements-dev.txt -e $(BACKEND_DIR)

ifeq ($(OS),Windows_NT)
venv: $(PY) ## Create .venv and install backend deps (activate: .venv\Scripts\Activate.ps1)
	@echo "venv ready -> .venv\\Scripts\\Activate.ps1"
else
venv: $(PY) ## Create .venv and install backend deps (activate: source .venv/bin/activate)
	@echo "venv ready -> source $(VENV)/bin/activate"
endif

install: $(PY) frontend/node_modules ## Install/update backend runtime deps (.venv) and frontend deps (npm)
	$(PY) -m pip install -r $(BACKEND_DIR)/requirements.txt

install-dev: install ## Also install dev deps and the backend app in editable mode
	$(PY) -m pip install -r $(BACKEND_DIR)/requirements-dev.txt -e $(BACKEND_DIR)

install-rag: $(PY) ## Install RAG deps in .venv (CPU-only torch, ~750MB instead of ~3.9GB with CUDA)
	$(PY) -m pip install --index-url https://download.pytorch.org/whl/cpu torch
	$(PY) -m pip install -r rag/requirements.txt

api-up: ## Build and start the backend API container (port 8000)
	docker compose up -d --build api

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci
	@touch frontend/node_modules

frontend: frontend/node_modules ## Start the Next.js dev server (foreground, port 3000)
	cd frontend && npm run dev

## ─── Infrastructure ─────────────────────────────────────────────────────────

up: ## Start PostgreSQL dev database (port 5432 via Docker)
	docker compose up -d postgres --remove-orphans
	@echo "Waiting for PostgreSQL to be ready..."
	@docker compose exec postgres sh -c 'until pg_isready -U genai_e2 -d genai_e2 > /dev/null 2>&1; do sleep 1; done'
	@echo "PostgreSQL is ready."
	@docker compose exec postgres psql -U genai_e2 -d genai_e2 \
	  -tc "SELECT 1 FROM pg_database WHERE datname='genai_e2_test'" \
	  | grep -q 1 \
	  || docker compose exec postgres psql -U genai_e2 -d genai_e2 \
	     -c "CREATE DATABASE genai_e2_test OWNER genai_e2;" \
	  && echo "Test database ready."

down: ## Stop all containers
	docker compose down --remove-orphans

db-init-local: ## Create role and databases in local PostgreSQL (requires PostgreSQL 16 running, see README)
	@PSQL='psql -U postgres'; \
	$$PSQL -tc 'SELECT 1' >/dev/null 2>&1 || PSQL='sudo -u postgres psql'; \
	$$PSQL -tc "SELECT 1 FROM pg_roles WHERE rolname='genai_e2'" | grep -q 1 \
	  || $$PSQL -c "CREATE ROLE genai_e2 WITH PASSWORD 'genai_e2_dev' LOGIN;"; \
	$$PSQL -tc "SELECT 1 FROM pg_database WHERE datname='genai_e2'" | grep -q 1 \
	  || $$PSQL -c "CREATE DATABASE genai_e2 OWNER genai_e2;"; \
	$$PSQL -tc "SELECT 1 FROM pg_database WHERE datname='genai_e2_test'" | grep -q 1 \
	  || $$PSQL -c "CREATE DATABASE genai_e2_test OWNER genai_e2;"
	@echo "Local PostgreSQL initialized: genai_e2 role and databases ready."

## ─── Migrations ─────────────────────────────────────────────────────────────

migrate: $(PY) ## Apply Alembic migrations to dev database
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) $(PY) -m alembic upgrade head

migrate-test: $(PY) ## Apply Alembic migrations to test database
	cd $(BACKEND_DIR) && DATABASE_URL=$(TEST_DB_URL) $(PY) -m alembic upgrade head

## ─── Tests ───────────────────────────────────────────────────────────────────

test: $(PY) ## Run full test suite
	cd $(BACKEND_DIR) && TEST_DATABASE_URL=$(TEST_DB_URL) $(PY) -m pytest -v

test-unit: $(PY) ## Run unit tests only (no DB required)
	cd $(BACKEND_DIR) && $(PY) -m pytest tests/test_jira_client.py -v

routing-eval: $(PY) ## Evaluate LLM squad classification against the golden set (requires Ollama, not part of make test)
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) LLM_ENABLED=true $(PY) -m scripts.routing_eval

## ─── API ──────────────────────────────────────────────────────────────────────

serve: $(PY) ## Start API locally, outside Docker (requires make up + make migrate first)
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) $(PY) -m uvicorn app.main:app --reload --port 8000

## ─── Demo ────────────────────────────────────────────────────────────────────

ingest-demo: ## POST the synthetic fixture to the local API
	@echo "Ingesting synthetic Freshservice ticket..."
	curl -s -X POST http://localhost:8000/api/v1/tickets/ingest \
	  -H "Content-Type: application/json" \
	  -d @$(BACKEND_DIR)/tests/fixtures/ticket_created.json | python3 -m json.tool

worker-once: $(PY) ## Claim and process one outbox event
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) $(PY) -m app.worker --once

poll-once: $(PY) ## Poll Freshservice once for tickets updated since the last sync
	cd $(BACKEND_DIR) && DATABASE_URL=$(DB_URL) $(PY) -m app.worker --poll-once

## ─── RAG ─────────────────────────────────────────────────────────────────────

rag-sync: $(PY) ## Incrementally index docs/**/*.md into rag/data/knowledge.db
	$(PY) -m rag.sync

rag-eval: $(PY) ## Run the RAG golden set and print recall@5
	$(PY) -m rag.golden.eval

rag-test: $(PY) ## Run the RAG test suite
	$(PY) -m pytest rag/tests -v

## ─── Spec-Driven Development (GitHub Spec Kit) ───────────────────────────────

spec: ## New spec: make spec D="descricao da feature" [NAME=short-name] [N=numero]
	@test -n '$(D)' || { echo 'Usage: make spec D="feature description" [NAME=short-name] [N=number]'; exit 1; }
	@$(SPECIFY) $(if $(NAME),--short-name '$(NAME)') $(if $(N),--number '$(N)') '$(D)'

spec-list: ## List existing feature specs
	@ls -1 specs 2>/dev/null || echo "no specs yet"

spec-current: ## Show the feature the Spec Kit commands are currently pointed at
	@cat .specify/feature.json 2>/dev/null || echo "no active feature"

sdd: ## Print the spec-driven workflow (slash commands to run inside Claude Code)
	@echo "1. make spec D=\"descricao\" NAME=short-name   # creates specs/NNN-short-name/spec.md"
	@echo "2. /speckit.specify   <descricao>             # fills the spec"
	@echo "3. /speckit.clarify                           # resolves open questions"
	@echo "4. /speckit.plan                              # plan.md + research/contracts"
	@echo "5. /speckit.tasks                             # tasks.md"
	@echo "6. /speckit.analyze                           # consistency check before coding"
	@echo "7. /speckit.implement                         # execute tasks.md"
	@echo "Active feature: make spec-current"

## ─── Maintenance ──────────────────────────────────────────────────────────────

clean: ## Remove Python caches and build artifacts (keeps .venv and node_modules)
	find . -path ./.venv -prune -o -path ./node_modules -prune -o \
	  \( -type d -name __pycache__ -o -type d -name .pytest_cache -o -type d -name "*.egg-info" \) \
	  -print -exec rm -rf {} + 2>/dev/null || true
	find . -path ./.venv -prune -o -name "*.pyc" -print -delete 2>/dev/null || true
