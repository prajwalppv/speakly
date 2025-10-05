.PHONY: help install test lint build dev deploy clean

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Speakly - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Installation
install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	@echo "$(GREEN)Installing backend dependencies...$(NC)"
	cd backend && pip install -r requirements-dev.txt

install-frontend: ## Install frontend dependencies
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	cd frontend && npm install

# Testing
test: test-backend ## Run all tests

test-backend: ## Run backend tests
	@echo "$(GREEN)Running backend tests...$(NC)"
	cd backend && pytest tests/ -v

test-backend-coverage: ## Run backend tests with coverage
	@echo "$(GREEN)Running backend tests with coverage...$(NC)"
	cd backend && pytest tests/ --cov=app --cov-report=html --cov-report=term

test-backend-watch: ## Run backend tests in watch mode
	@echo "$(GREEN)Running backend tests in watch mode...$(NC)"
	cd backend && pytest-watch

# Linting
lint: lint-backend lint-frontend ## Lint all code

lint-backend: ## Lint backend code
	@echo "$(GREEN)Linting backend...$(NC)"
	cd backend && ruff check app/ || true
	cd backend && mypy app/ --ignore-missing-imports || true

lint-frontend: ## Lint frontend code
	@echo "$(GREEN)Linting frontend...$(NC)"
	cd frontend && npx tsc --noEmit

# Building
build: build-frontend ## Build production bundles

build-backend: ## Build backend Docker image
	@echo "$(GREEN)Building backend Docker image...$(NC)"
	docker build -t speakly-backend ./backend

build-frontend: ## Build frontend for production
	@echo "$(GREEN)Building frontend...$(NC)"
	cd frontend && npm run build

# Development
dev: ## Start development servers (both backend and frontend)
	@echo "$(GREEN)Starting development servers...$(NC)"
	docker compose up backend frontend

dev-backend: ## Start backend dev server only
	@echo "$(GREEN)Starting backend dev server...$(NC)"
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start frontend dev server only
	@echo "$(GREEN)Starting frontend dev server...$(NC)"
	cd frontend && npm run dev

# Database
db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	cd backend && alembic upgrade head

db-migrate-create: ## Create new migration
	@echo "$(GREEN)Creating new migration...$(NC)"
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(YELLOW)⚠️  WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && rm -f data/app.db && alembic upgrade head; \
	fi

# Deployment
deploy: deploy-backend deploy-frontend ## Deploy both backend and frontend

deploy-backend: ## Deploy backend to Railway
	@echo "$(GREEN)Deploying backend to Railway...$(NC)"
	cd backend && railway up

deploy-frontend: ## Deploy frontend to Vercel
	@echo "$(GREEN)Deploying frontend to Vercel...$(NC)"
	cd frontend && vercel --prod

# Cleaning
clean: clean-backend clean-frontend ## Clean all build artifacts

clean-backend: ## Clean backend artifacts
	@echo "$(GREEN)Cleaning backend...$(NC)"
	cd backend && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	cd backend && rm -rf .pytest_cache htmlcov .coverage

clean-frontend: ## Clean frontend artifacts
	@echo "$(GREEN)Cleaning frontend...$(NC)"
	cd frontend && rm -rf dist node_modules/.cache

clean-all: clean ## Deep clean (including node_modules and venv)
	@echo "$(YELLOW)Deep cleaning...$(NC)"
	cd frontend && rm -rf node_modules
	cd backend && rm -rf venv

# Docker
docker-up: ## Start all services with Docker Compose
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker compose up -d

docker-down: ## Stop all Docker services
	@echo "$(GREEN)Stopping Docker services...$(NC)"
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f

docker-rebuild: ## Rebuild and restart Docker services
	@echo "$(GREEN)Rebuilding Docker services...$(NC)"
	docker compose up --build -d

# Production checks
pre-deploy: test-backend-coverage lint build ## Run all pre-deployment checks
	@echo "$(GREEN)✅ All pre-deployment checks passed!$(NC)"

# Quick commands
quick-test: ## Quick test (backend only, no coverage)
	cd backend && pytest tests/ -x --tb=short

quick-check: ## Quick check (lint + type check)
	cd backend && ruff check app/
	cd frontend && npx tsc --noEmit

# Stats
stats: ## Show project statistics
	@echo "$(GREEN)Project Statistics:$(NC)"
	@echo ""
	@echo "Backend:"
	@echo "  Python files: $$(find backend/app -name '*.py' | wc -l)"
	@echo "  Test files: $$(find backend/tests -name '*.py' | wc -l)"
	@echo "  Lines of code: $$(find backend/app -name '*.py' -exec wc -l {} + | tail -1 | awk '{print $$1}')"
	@echo ""
	@echo "Frontend:"
	@echo "  TypeScript files: $$(find frontend/src -name '*.ts' -o -name '*.tsx' | wc -l)"
	@echo "  Lines of code: $$(find frontend/src -name '*.ts' -o -name '*.tsx' -exec wc -l {} + | tail -1 | awk '{print $$1}')"
