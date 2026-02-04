# AI-Academy 3 ATI Stats - Development Makefile

.PHONY: help install dev-setup run test lint format clean docker-up docker-down db-migrate db-upgrade db-downgrade db-revision


# Default target
help:
	@echo "ATI Stats - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev-setup    Set up complete development environment"
	@echo ""
	@echo "Development:"
	@echo "  make run          Run the development server"
	@echo "  make test         Run test suite"
	@echo "  make lint         Run linting checks"
	@echo "  make format       Format code with black and ruff"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    Start Docker services (database, redis)"
	@echo "  make docker-down  Stop Docker services"
	@echo ""
	@echo "Database:"
	@echo "  make db-upgrade   Run database migrations"
	@echo "  make db-downgrade Rollback last migration"
	@echo "  make db-revision  Create new migration (usage: make db-revision msg='description')"
	@echo "  make db-current   Show current migration revision"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        Remove cache files and build artifacts"


# Install production dependencies
install:
	pip install -r requirements.txt

# Set up development environment
dev-setup:
	python -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source .venv/bin/activate  (Linux/macOS)"
	@echo "  .venv\\Scripts\\activate     (Windows)"
	@echo ""
	@echo "Then run: make install"
	@echo "Copy .env.example to .env and configure your settings"

# Run development server
run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest -v

# Run tests with coverage
test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing

# Run linting
lint:
	ruff check src tests
	mypy src

# Format code
format:
	black src tests
	ruff check --fix src tests

# Start Docker services
docker-up:
	docker-compose up -d

# Stop Docker services
docker-down:
	docker-compose down

# Start Docker services with tools (includes pgAdmin)
docker-up-tools:
	docker-compose --profile tools up -d

# Clean up cache files
# Database migrations
db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-revision:
	alembic revision --autogenerate -m "$(msg)"

db-current:
	alembic current

db-history:
	alembic history

# Clean up cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	@echo "Cleaned up cache files"
