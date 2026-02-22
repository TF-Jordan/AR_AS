# ==============================================================================
# Makefile for AR_AS RaaS Platform
# ==============================================================================

.PHONY: help build up down restart logs clean test

.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# ==============================================================================
# HELP
# ==============================================================================
help: ## Show this help message
	@echo "$(BLUE)==================================================================$(NC)"
	@echo "$(BLUE)  AR_AS RaaS Platform - Commands$(NC)"
	@echo "$(BLUE)==================================================================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==============================================================================
# DOCKER
# ==============================================================================
build: ## Build all Docker images
	@echo "$(BLUE)Building all Docker images...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)Build complete!$(NC)"

up: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)All services started!$(NC)"
	@echo "$(YELLOW)API:     http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs:    http://localhost:8000/docs$(NC)"

up-build: ## Build and start all services
	docker-compose up -d --build

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

restart-api: ## Restart only the API service
	docker-compose restart api

# ==============================================================================
# LOGS
# ==============================================================================
logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show logs from API service
	docker-compose logs -f api

logs-postgres: ## Show logs from PostgreSQL
	docker-compose logs -f postgres

status: ## Show status of all services
	@docker-compose ps

# ==============================================================================
# DATABASE
# ==============================================================================
init-db: ## Initialize database schema
	@echo "$(BLUE)Initializing database schema...$(NC)"
	docker-compose exec api python main.py init-db
	@echo "$(GREEN)Database initialized!$(NC)"

shell-postgres: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-ar_as_db}

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

# ==============================================================================
# TESTING
# ==============================================================================
test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)Tests complete!$(NC)"

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

# ==============================================================================
# CLEANUP
# ==============================================================================
clean: ## Remove stopped containers
	docker-compose down --remove-orphans
	docker system prune -f

# ==============================================================================
# HEALTH
# ==============================================================================
health: ## Check health of all services
	@curl -sf http://localhost:8000/health || echo "$(RED)API not healthy$(NC)"

# ==============================================================================
# QUICK START
# ==============================================================================
quickstart: ## Quick start: build, start, and initialize
	@echo "$(BLUE)Setting up AR_AS RaaS Platform...$(NC)"
	@make build
	@make up
	@echo "$(YELLOW)Waiting for services...$(NC)"
	@sleep 15
	@make init-db
	@echo ""
	@echo "$(GREEN)AR_AS RaaS Platform is ready!$(NC)"
	@echo "  API:  http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"
