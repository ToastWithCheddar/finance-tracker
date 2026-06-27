# Makefile — repo-root orchestrator for tests, benchmarks, and the prod stack.
#
# Promoted to repo root by IW-2. All targets are relative to the
# repo root, regardless of cwd. Invoke as:
#   make <target>
#
# Test sources, benchmarks, and ops/observability configuration now live in
# their canonical homes under backend/, frontend/, ml-worker/, e2e/,
# benchmarks/, and ops/.

MAKEFILE_DIR := $(dir $(realpath $(firstword $(MAKEFILE_LIST))))
REPO_ROOT    := $(realpath $(MAKEFILE_DIR))

TESTS_BACKEND    := $(REPO_ROOT)/backend
TESTS_FRONTEND   := $(REPO_ROOT)/frontend
TESTS_ML         := $(REPO_ROOT)/ml-worker
TESTS_E2E        := $(REPO_ROOT)/e2e
BENCH_BACKEND    := $(REPO_ROOT)/benchmarks/backend
BENCH_FRONTEND   := $(REPO_ROOT)/benchmarks/frontend
BACKEND_SRC      := $(REPO_ROOT)/backend

PYTHON ?= python3.11
NPM    ?= npm

.DEFAULT_GOAL := help

PROD_COMPOSE := $(REPO_ROOT)/docker-compose.prod.yml
OBS_COMPOSE  := $(REPO_ROOT)/docker-compose.observability.yml

.PHONY: help \
        install-backend install-frontend install-ml-worker \
        install-bench-backend install-bench-frontend install-all \
        test-backend test-frontend test-ml-worker test-all e2e \
        bench-backend bench-frontend bench-all \
        lint clean \
        prod-config-check prod-up prod-down \
        backup restore

## ---------------------------------------------------------------------------
## help
## ---------------------------------------------------------------------------

help: ## List available targets
	@echo "Makefile — available targets:"
	@echo ""
	@echo "  install:"
	@echo "    install-backend         venv + pip install -e backend[dev] (test deps live in dev extra)"
	@echo "    install-frontend        npm ci in frontend/"
	@echo "    install-ml-worker       venv + pip install -e in ml-worker/tests"
	@echo "    install-bench-backend   venv + pip install -e in benchmarks/backend"
	@echo "    install-bench-frontend  npm ci in benchmarks/frontend"
	@echo "    install-all             all of the above"
	@echo ""
	@echo "  test:"
	@echo "    test-backend            run pytest under backend/ (Docker required for testcontainers)"
	@echo "    test-frontend           run vitest under frontend/"
	@echo "    test-ml-worker          run pytest under ml-worker/tests"
	@echo "    test-all                run all three test subtrees (e2e excluded — needs live stack)"
	@echo "    e2e                     run Playwright in e2e/ — requires npm install + npx playwright install + a live stack"
	@echo ""
	@echo "  bench:"
	@echo "    bench-backend           run capture_baseline.sh; needs LIVE stack on \$$BENCH_HOST"
	@echo "    bench-frontend          run capture_baseline.sh; needs built frontend/dist/"
	@echo "    bench-all               run both benchmarks (pre-conditions must be met)"
	@echo ""
	@echo "  prod stack:"
	@echo "    prod-config-check       docker compose config -q on docker-compose.prod.yml"
	@echo "    prod-up                 bring up the production stack (build prod targets)"
	@echo "    prod-down               tear down the production stack (ARGS=-v removes volumes)"
	@echo "    backup                  one-shot pg_dump | gzip | s3 cp (uses .env)"
	@echo "    restore                 stream KEY=<s3 object key> from BACKUP_BUCKET back into postgres"
	@echo ""
	@echo "  quality:"
	@echo "    lint                    ruff (backend + ml-worker tests) + npm run lint if defined"
	@echo "    clean                   remove .venv, node_modules, __pycache__, .pytest_cache under test/bench dirs"

## ---------------------------------------------------------------------------
## install targets
## ---------------------------------------------------------------------------

install-backend: ## Install backend tests (test deps via -e backend[dev])
	cd $(TESTS_BACKEND) && $(PYTHON) -m venv .venv
	$(TESTS_BACKEND)/.venv/bin/pip install --upgrade pip
	$(TESTS_BACKEND)/.venv/bin/pip install -e "$(BACKEND_SRC)[dev]"

install-frontend: ## npm ci under frontend/
	cd $(TESTS_FRONTEND) && $(NPM) ci

install-ml-worker: ## Install ml-worker tests
	cd $(TESTS_ML)/tests && $(PYTHON) -m venv .venv
	$(TESTS_ML)/tests/.venv/bin/pip install --upgrade pip
	$(TESTS_ML)/tests/.venv/bin/pip install -e $(TESTS_ML)/tests

install-bench-backend: ## Install backend benchmark harness
	cd $(BENCH_BACKEND) && $(PYTHON) -m venv .venv
	$(BENCH_BACKEND)/.venv/bin/pip install --upgrade pip
	$(BENCH_BACKEND)/.venv/bin/pip install -e $(BENCH_BACKEND)

install-bench-frontend: ## npm ci under benchmarks/frontend
	cd $(BENCH_FRONTEND) && $(NPM) ci

install-all: install-backend install-frontend install-ml-worker install-bench-backend install-bench-frontend ## Install everything

## ---------------------------------------------------------------------------
## test targets
## ---------------------------------------------------------------------------

test-backend: ## pytest in backend/ (requires Docker)
	cd $(TESTS_BACKEND) && .venv/bin/pytest -x -v

test-frontend: ## vitest in frontend/
	cd $(TESTS_FRONTEND) && $(NPM) test

test-ml-worker: ## pytest in ml-worker/tests
	cd $(TESTS_ML)/tests && .venv/bin/pytest -x -v

test-all: test-backend test-frontend test-ml-worker ## Run backend + frontend + ml-worker test subtrees (e2e excluded)

# Pre-conditions: cd e2e && npm install && npx playwright install, plus a
# running app stack the Playwright config can hit. e2e is intentionally NOT a
# dependency of test-all — Playwright cannot run in a vacuum.
e2e: ## Run Playwright suite in e2e/ — requires `npm install` + `npx playwright install` + a live stack
	cd $(TESTS_E2E) && $(NPM) test

## ---------------------------------------------------------------------------
## bench targets
## ---------------------------------------------------------------------------
##
## Pre-conditions:
##   bench-backend  : the full app stack must be reachable at $$BENCH_HOST
##                    (default http://localhost:8000). The script does NOT
##                    start services. See benchmarks/backend/README.md.
##   bench-frontend : frontend/dist/ must exist (run `npm run build` in
##                    frontend/) before invoking. See benchmarks/frontend.

bench-backend: ## Locust 60s baseline; needs live stack
	cd $(BENCH_BACKEND) && bash scripts/capture_baseline.sh

bench-frontend: ## Frontend perf baseline; needs frontend/dist/
	cd $(BENCH_FRONTEND) && bash scripts/capture_baseline.sh

bench-all: bench-backend bench-frontend ## Run both benchmark suites

## ---------------------------------------------------------------------------
## lint / clean
## ---------------------------------------------------------------------------

lint: ## ruff + npm lint (non-fatal placeholders if tools absent)
	@echo "[lint] ruff: backend/tests"
	@command -v ruff >/dev/null 2>&1 && ruff check $(TESTS_BACKEND)/tests || echo "[lint] ruff not installed; skipping backend lint"
	@echo "[lint] ruff: ml-worker/tests"
	@command -v ruff >/dev/null 2>&1 && ruff check $(TESTS_ML)/tests || echo "[lint] ruff not installed; skipping ml-worker lint"
	@echo "[lint] frontend npm run lint (if defined)"
	@cd $(TESTS_FRONTEND) && \
	  if $(NPM) run | grep -qE '^\s+lint'; then \
	    $(NPM) run lint; \
	  else \
	    echo "[lint] no 'lint' script in frontend/package.json; skipping"; \
	  fi

## ---------------------------------------------------------------------------
## prod stack targets
## ---------------------------------------------------------------------------

prod-config-check: ## Validate docker-compose.prod.yml
	@echo "[prod] docker compose config -q $(PROD_COMPOSE)"
	@if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
	  docker compose -f $(PROD_COMPOSE) config -q && echo "[prod] OK (docker daemon)"; \
	elif command -v yamllint >/dev/null 2>&1; then \
	  yamllint -d "{extends: relaxed, rules: {line-length: disable}}" $(PROD_COMPOSE) && echo "[prod] OK (yamllint)"; \
	else \
	  $(PYTHON) -c "import yaml,sys; yaml.safe_load(open(sys.argv[1])); print('[prod] OK (python yaml.safe_load)')" $(PROD_COMPOSE); \
	fi

tls-cert: ## Regenerate self-signed nginx TLS certs (closes INFRA-NGINX-001)
	@mkdir -p nginx/ssl
	openssl req -x509 -newkey rsa:2048 -nodes \
	  -keyout nginx/ssl/privkey.pem \
	  -out nginx/ssl/fullchain.pem \
	  -days 365 -subj "/CN=localhost" \
	  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
	@echo "[tls] cert regenerated under nginx/ssl/. Operator: replace with real CA-signed certs for staging/prod."

prod-up: ## Bring up the production stack (TLS will use nginx/ssl/*.pem if present)
	@test -f nginx/ssl/fullchain.pem || (echo "[prod-up] no TLS cert; run 'make tls-cert' first or stack will serve HTTP only on :80" && true)
	docker compose -f $(PROD_COMPOSE) up -d --build

prod-down: ## Tear down the production stack (use ARGS=-v to drop volumes)
	docker compose -f $(PROD_COMPOSE) down $(ARGS)

backup: ## One-shot pg_dump to S3 — needs BACKUP_BUCKET in env
	@test -n "$$BACKUP_BUCKET" || { echo "BACKUP_BUCKET must be set"; exit 1; }
	docker compose -f $(PROD_COMPOSE) exec -T postgres \
	  pg_dump -U $${POSTGRES_USER:-postgres} --no-owner | gzip -9 \
	  | aws s3 cp - "s3://$$BACKUP_BUCKET/postgres/$$(date -u +%Y/%m/%d)/manual-$$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

restore: ## Stream KEY=<s3 object key> from BACKUP_BUCKET into postgres
	@test -n "$$BACKUP_BUCKET" -a -n "$$KEY" || { echo "BACKUP_BUCKET and KEY required"; exit 1; }
	aws s3 cp "s3://$$BACKUP_BUCKET/$$KEY" - \
	  | gunzip \
	  | docker compose -f $(PROD_COMPOSE) exec -T postgres \
	      psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-finance_tracker}

clean: ## Remove venvs, node_modules, caches under test/bench dirs
	@echo "[clean] removing .venv directories under backend/ frontend/ ml-worker/ e2e/ benchmarks/"
	@for d in $(TESTS_BACKEND) $(TESTS_FRONTEND) $(TESTS_ML) $(TESTS_E2E) $(REPO_ROOT)/benchmarks; do \
	  find $$d -type d -name ".venv" -prune -exec rm -rf {} + 2>/dev/null || true; \
	  find $$d -type d -name "node_modules" -prune -exec rm -rf {} + 2>/dev/null || true; \
	  find $$d -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true; \
	  find $$d -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true; \
	done
	@echo "[clean] done"
