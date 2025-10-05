# Speakly developer utilities

.DEFAULT_GOAL := help

COMPOSE ?= docker compose
LOCAL_SERVICES := db backend frontend

GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Show this help message
	@echo "$(GREEN)Speakly Commands$(NC)"
	@echo
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-22s$(NC) %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local development (Docker)
# ---------------------------------------------------------------------------

local-up: ## Run Postgres, backend (uvicorn), and frontend (Vite) with Docker
	$(COMPOSE) up --build $(LOCAL_SERVICES)

local-up-detached: ## Run local stack in the background
	$(COMPOSE) up -d --build $(LOCAL_SERVICES)

local-down: ## Stop services (containers preserved)
	$(COMPOSE) down

local-reset: ## Stop and remove services, networks, and data volumes
	$(COMPOSE) down --volumes --remove-orphans

local-logs: ## Tail logs from db, backend, and frontend containers
	$(COMPOSE) logs -f $(LOCAL_SERVICES)

backend-shell: ## Open a shell inside the backend container (requires running stack)
	$(COMPOSE) exec backend bash

frontend-shell: ## Open a shell inside the frontend container (requires running stack)
	$(COMPOSE) exec frontend sh

local-migrate: ## Run Alembic migrations against the local Postgres database
	$(COMPOSE) run --rm backend alembic upgrade head

backend-tests: ## Run backend pytest suite inside container
	$(COMPOSE) run --rm backend-tests

# ---------------------------------------------------------------------------
# Frontend / backend convenience commands (host machine)
# ---------------------------------------------------------------------------

frontend-build: ## Build the Vite project for production assets
	cd frontend && npm run build

backend-format: ## Format backend code (ruff + black) if available
	cd backend && ruff check app --fix
	cd backend && ruff format app

# ---------------------------------------------------------------------------
# Fly.io deployment helpers
# ---------------------------------------------------------------------------

fly-deploy: fly-auth fly-ensure-db fly-deploy-backend fly-deploy-frontend ## Deploy backend and frontend to Fly.io

fly-auth: ## Ensure you are logged in to Fly.io (no-op if already authenticated)
	@if ! flyctl auth whoami >/dev/null 2>&1; then \
		echo "$(YELLOW)Logging into Fly.io...$(NC)"; \
		flyctl auth login; \
	else \
		echo "$(GREEN)Already authenticated with Fly.io$(NC)"; \
	fi

fly-ensure-db: ## Start the Fly Postgres app if it is stopped
	@if [ -z "$(FLY_POSTGRES_APP)" ]; then \
		echo "$(YELLOW)Set FLY_POSTGRES_APP to your Fly Postgres app name before running this command.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Ensuring Fly Postgres app '$(FLY_POSTGRES_APP)' is running...$(NC)"
	@status=$$(flyctl status --app $(FLY_POSTGRES_APP) --json); \
	running=$$(echo "$$status" | jq -r '[.Machines[]?.State == "started"] | all'); \
	if [ "$$running" != "true" ]; then \
		echo "$(YELLOW)Postgres machines stopped; starting now...$(NC)"; \
		flyctl machine start --app $(FLY_POSTGRES_APP); \
		flyctl status --app $(FLY_POSTGRES_APP); \
	else \
		echo "$(GREEN)Postgres machines already running.$(NC)"; \
	fi

fly-deploy-backend: ## Deploy backend using fly.toml (requires flyctl login & secrets)
	flyctl deploy --config fly.toml --remote-only --strategy immediate --app speakly-backend
	$(MAKE) fly-start-backend

fly-deploy-frontend: ## Deploy frontend using frontend/fly.toml (expects Vite args via secrets/vars)
	flyctl deploy \
	  --config frontend/fly.toml \
	  --remote-only \
	  --strategy immediate \
	  --build-arg VITE_CLERK_PUBLISHABLE_KEY=$${VITE_CLERK_PUBLISHABLE_KEY:?set VITE_CLERK_PUBLISHABLE_KEY} \
	  --build-arg VITE_API_BASE_URL=$${VITE_API_BASE_URL:?set VITE_API_BASE_URL}
	$(MAKE) fly-start-frontend

fly-logs-backend: ## Tail backend logs from Fly.io
	flyctl logs --app speakly-backend

fly-logs-frontend: ## Tail frontend logs from Fly.io
	flyctl logs --app speakly-frontend

fly-logs-db: ## Tail database logs from Fly.io Postgres cluster
	flyctl logs --app speakly-db

fly-start-backend: ## Ensure backend Fly machines are running
	@bash -euo pipefail -c 'status=$$(flyctl status --app speakly-backend --json); pending=$$(echo "$$status" | jq -r ".Machines[]? | select(.State != \"started\") | .ID"); if [ -n "$$pending" ]; then echo "Starting backend machines..."; for id in $$pending; do echo "  -> $$id"; flyctl machines start --app speakly-backend "$$id"; done; flyctl status --app speakly-backend; else echo "Backend machines already running."; fi'

fly-start-frontend: ## Ensure frontend Fly machines are running
	@bash -euo pipefail -c 'status=$$(flyctl status --app speakly-frontend --json); pending=$$(echo "$$status" | jq -r ".Machines[]? | select(.State != \"started\") | .ID"); if [ -n "$$pending" ]; then echo "Starting frontend machines..."; for id in $$pending; do echo "  -> $$id"; flyctl machines start --app speakly-frontend "$$id"; done; flyctl status --app speakly-frontend; else echo "Frontend machines already running."; fi'

# ---------------------------------------------------------------------------
# Misc utilities
# ---------------------------------------------------------------------------

clean: ## Remove Python and Node build artifacts from the workspace
	rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/node_modules/.cache
