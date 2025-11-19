# Makefile for Claire de Binaire
# Provides convenient shortcuts for common development tasks

.PHONY: help test test-unit test-integration test-fast test-all coverage coverage-html clean install setup lint

# Default target
help:
	@echo "Claire de Binaire - Development Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only (fast)"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-fast     - Run unit tests without coverage"
	@echo "  make coverage      - Run tests with coverage report"
	@echo "  make coverage-html - Generate HTML coverage report"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install development dependencies"
	@echo "  make setup         - Full development environment setup"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove generated files and caches"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"
	@echo "  make docker-health - Check Docker services health"

# Testing targets
test:
	@echo "🧪 Running all tests..."
	python -m pytest -v

test-unit:
	@echo "⚡ Running unit tests..."
	python -m pytest -v -m unit

test-integration:
	@echo "🔗 Running integration tests..."
	python -m pytest -v -m integration

test-fast:
	@echo "⚡ Running fast tests (no coverage)..."
	python -m pytest -v -m unit --tb=short -q

test-all:
	@echo "🧪 Running all tests with coverage..."
	python -m pytest -v --cov=services --cov-report=term-missing

# Coverage targets
coverage:
	@echo "📊 Running tests with coverage..."
	python -m pytest --cov=services --cov-report=term-missing --cov-report=json
	@echo ""
	@echo "✅ Coverage report generated"

coverage-html:
	@echo "📊 Generating HTML coverage report..."
	python -m pytest --cov=services --cov-report=html
	@echo ""
	@echo "✅ HTML report generated in htmlcov/"
	@echo "   Open: htmlcov/index.html"

coverage-check:
	@echo "🔍 Checking coverage threshold (95%)..."
	python -m pytest --cov=services --cov-fail-under=95 -q

# Setup targets
install:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements-dev.txt
	@echo "✅ Dependencies installed"

setup:
	@echo "🚀 Setting up development environment..."
	@bash scripts/setup-dev.sh
	@echo "✅ Development environment ready"

# Docker targets
docker-up:
	@echo "🐳 Starting Docker services..."
	docker compose up -d
	@echo "✅ Services started"

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker compose down
	@echo "✅ Services stopped"

docker-health:
	@echo "🏥 Checking Docker services health..."
	@docker compose ps
	@echo ""
	@docker compose exec -T cdb_postgres pg_isready -U claire_admin || echo "⚠️  PostgreSQL not ready"
	@docker compose exec -T cdb_redis redis-cli ping || echo "⚠️  Redis not ready"

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker compose logs --tail=50

# Cleanup targets
clean:
	@echo "🧹 Cleaning up generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "coverage.json" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Quick development workflow
dev-check: test-fast coverage-check
	@echo ""
	@echo "✅ Quick dev check complete"

# Pre-commit simulation
pre-commit:
	@echo "🔍 Running pre-commit checks..."
	@bash .git/hooks/pre-commit || echo "⚠️  Pre-commit hook not installed"
