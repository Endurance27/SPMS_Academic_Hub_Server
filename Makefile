.PHONY: help install dev-install up down restart logs test coverage lint format

# Colors for output
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)
	

help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo "  make up            - Start all services"
	@echo "  make down          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo "  make logs          - View logs"
	@echo "  make test          - Run tests"
	@echo "  make coverage      - Run tests with coverage"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make migrate       - Run database migrations"
	@echo "  make seed          - Seed database with initial data"
	@echo '${GREEN}Backend Template - Available Commands${RESET}'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "${YELLOW}%-20s${RESET} %s\n", $$1, $$2}'

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt
	pre-commit install

up:
	docker-compose up -d
	@echo "${GREEN}All services started!${RESET}"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/api/v1/docs"
	@echo "Flower: http://localhost:5555"
	@echo "Kibana: http://localhost:5601"

down:
	docker-compose down
	@echo "${YELLOW}All services stopped${RESET}"

restart: ## Restart all services
	docker-compose restart
	@echo "${GREEN}All services restarted!${RESET}"

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

logs-celery: ## View Celery worker logs
	docker-compose logs -f celery_worker

logs-db: ## View PostgreSQL logs
	docker-compose logs -f postgres

build: ## Build Docker images
	docker-compose build
	@echo "${GREEN}Docker images built!${RESET}"

ps: ## List running containers
	docker-compose ps

# ============================================================================
# Database Commands
# ============================================================================
init-db: ## Initialize database tables
	docker-compose exec -T -u $$(id -u):$$(id -g) -e PYTHONPATH=/app api python scripts/init_db.py
	@echo "${GREEN}Database initialized!${RESET}"

migrate: ## Run database migrations
	docker-compose exec -T -u $$(id -u):$$(id -g) api alembic upgrade head
	@echo "${GREEN}Migrations applied!${RESET}"

migrate-create: ## Create new migration
	@read -p "Enter migration message: " msg; \
	docker-compose exec -T -u $$(id -u):$$(id -g) api alembic revision --autogenerate -m "$$msg"
	@echo "${GREEN}Migration created!${RESET}"

migrate-rollback: ## Rollback last migration
	docker-compose exec -T -u $$(id -u):$$(id -g) api alembic downgrade -1
	@echo "${YELLOW}Rolled back last migration${RESET}"

migrate-history: ## View migration history
	docker-compose exec -T -u $$(id -u):$$(id -g) api alembic history

migrate-current: ## Show current migration version
	docker-compose exec -T -u $$(id -u):$$(id -g) api alembic current

seed: ## Seed database with initial data
	docker-compose exec -T -u $$(id -u):$$(id -g) -e PYTHONPATH=/app api python scripts/seed_data.py
	@echo "${GREEN}Database seeded with demo data!${RESET}"

seed-permissions: ## Seed permissions and roles
	docker-compose exec -T -u $$(id -u):$$(id -g) -e PYTHONPATH=/app api python scripts/seed_permissions.py
	@echo "${GREEN}Permissions and roles seeded!${RESET}"

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U app_user -d app_db

db-backup: ## Backup database
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U app_user app_db > backups/app_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}Database backed up to backups/${RESET}"

db-restore: ## Restore database from backup (use: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "${YELLOW}Please specify backup file: make db-restore FILE=backup.sql${RESET}"; \
		exit 1; \
	fi
	docker-compose exec -T postgres psql -U app_user -d app_db < $(FILE)
	@echo "${GREEN}Database restored from $(FILE)${RESET}"

# ============================================================================
# Testing
# ============================================================================
test: ## Run all tests
	pytest tests/ -v
	@echo "${GREEN}Tests completed!${RESET}"

test-unit: ## Run unit tests
	pytest tests/unit/ -v

test-integration: ## Run integration tests
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v

coverage: ## Run tests with coverage report
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo "${GREEN}Coverage report generated in htmlcov/${RESET}"
	@echo "Open htmlcov/index.html in browser"

coverage-xml: ## Generate XML coverage report for CI
	pytest tests/ --cov=app --cov-report=xml

test-watch: ## Run tests in watch mode
	ptw tests/ -- -v


# ============================================================================
# Code Quality
# ============================================================================
lint: ## Run all linters
	@echo "${YELLOW}Running Black...${RESET}"
	black --check app tests
	@echo "${YELLOW}Running isort...${RESET}"
	isort --check-only app tests
	@echo "${YELLOW}Running Flake8...${RESET}"
	flake8 app tests --max-line-length=100
	@echo "${YELLOW}Running Pylint...${RESET}"
	pylint app --disable=C0111,R0903
	@echo "${YELLOW}Running MyPy...${RESET}"
	mypy app
	@echo "${YELLOW}Running Bandit (Security)...${RESET}"
	bandit -r app -ll
	@echo "${GREEN}All linters passed!${RESET}"

format: ## Format code with Black and isort
	black app tests
	isort app tests
	@echo "${GREEN}Code formatted!${RESET}"

# pre-commit install

black:
	black .
isort:
	isort .

type-check: ## Run type checking with MyPy
	mypy app

security-check: ## Run security checks with Bandit
	bandit -r app -ll

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# ============================================================================
# Celery Commands
# ============================================================================
celery-worker: ## Start Celery worker
	celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

celery-beat: ## Start Celery beat scheduler
	celery -A app.tasks.celery_app beat --loglevel=info

flower: ## Start Flower (Celery monitoring)
	celery -A app.tasks.celery_app flower --port=5555

celery-purge: ## Purge all Celery tasks
	celery -A app.tasks.celery_app purge -f
	@echo "${YELLOW}All Celery tasks purged${RESET}"

celery-status: ## Check Celery worker status
	celery -A app.tasks.celery_app status

# ============================================================================
# Development
# ============================================================================
dev: ## Start API in development mode
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-https: ## Start API with HTTPS in development
	uvicorn app.main:app --host 0.0.0.0 --port 8443 --reload --ssl-keyfile=./certs/key.pem --ssl-certfile=./certs/cert.pem

shell: ## Open Python shell with app context
	python -c "from app.core.database import AsyncSessionLocal; from app.models import *; import asyncio; asyncio.run(AsyncSessionLocal())"

ipython: ## Open IPython shell
	ipython

# ============================================================================
# Production
# ============================================================================
prod-up: ## Start production services
	docker-compose -f docker-compose.prod.yml up -d
	@echo "${GREEN}Production services started!${RESET}"

prod-down: ## Stop production services
	docker-compose -f docker-compose.prod.yml down

prod-logs: ## View production logs
	docker-compose -f docker-compose.prod.yml logs -f

prod-build: ## Build production images
	docker-compose -f docker-compose.prod.yml build

prod-deploy: prod-build prod-down prod-up migrate seed-permissions ## Full production deployment
	@echo "${GREEN}Production deployment complete!${RESET}"

# ============================================================================
# Monitoring
# ============================================================================
health: ## Check health of all services
	@echo "${YELLOW}Checking service health...${RESET}"
	@curl -f http://localhost:8000/health && echo "${GREEN}API: Healthy${RESET}" || echo "${RED}API: Unhealthy${RESET}"
	@docker-compose exec postgres pg_isready && echo "${GREEN}PostgreSQL: Healthy${RESET}" || echo "${RED}PostgreSQL: Unhealthy${RESET}"
	@docker-compose exec redis redis-cli ping && echo "${GREEN}Redis: Healthy${RESET}" || echo "${RED}Redis: Unhealthy${RESET}"

stats: ## Show Docker stats
	docker stats --no-stream

top: ## Show running processes in containers
	docker-compose top

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "${GREEN}Cleanup complete!${RESET}"

clean-docker: ## Remove all Docker containers and images
	docker-compose down --rmi all --volumes --remove-orphans
	@echo "${YELLOW}All Docker resources cleaned${RESET}"

clean-all: clean clean-docker ## Remove all generated files and Docker resources

# ============================================================================
# Documentation
# ============================================================================
docs: ## Generate API documentation
	@echo "API Documentation: http://localhost:8000/api/v1/docs"
	@echo "ReDoc: http://localhost:8000/api/v1/redoc"

open-docs: ## Open API documentation in browser
	@python -m webbrowser http://localhost:8000/api/v1/docs

# ============================================================================
# Utilities
# ============================================================================
env-example: ## Create .env from .env.example
	cp .env.example .env
	@echo "${GREEN}.env file created. Please update with your values.${RESET}"

generate-secret: ## Generate a secure secret key
	@python -c "import secrets; print(secrets.token_urlsafe(32))"

check-deps: ## Check for outdated dependencies
	pip list --outdated

upgrade-deps: ## Upgrade all dependencies
	pip install --upgrade pip
	pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U

create-admin: ## Create admin user interactively
	python scripts/create_admin.py

# ============================================================================
# Quick Start
# ============================================================================
quick-start: install up init-db migrate seed seed-permissions ## Quick start for new setup
	@echo "${GREEN}==================================================${RESET}"
	@echo "${GREEN}Backend Template is ready!${RESET}"
	@echo "${GREEN}==================================================${RESET}"
	@echo ""
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/api/v1/docs"
	@echo "Flower: http://localhost:5555"
	@echo "Kibana: http://localhost:5601"
	@echo ""
	@echo "Default Admin Credentials:"
	@echo "Email: admin@example.com"
	@echo "Password: Admin@123"
	@echo ""
	@echo "${YELLOW}IMPORTANT: Change default passwords in production!${RESET}"

# ============================================================================
# CI/CD
# ============================================================================
ci: lint test coverage-xml ## Run CI pipeline
	@echo "${GREEN}CI pipeline completed!${RESET}"

ci-fast: format test ## Fast CI without full linting
	@echo "${GREEN}Fast CI completed!${RESET}"
