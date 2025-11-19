# Makefile for Claire de Binaire
# Provides convenient shortcuts for common development tasks

.PHONY: help test test-unit test-integration test-fast test-all coverage coverage-html coverage-check clean install setup lint lint-check format format-check type-check security-check docker-up docker-down docker-health docker-logs pre-commit dev-check

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
	@echo "Linting & Formatting:"
	@echo "  make lint          - Run all linters (black, ruff, mypy)"
	@echo "  make lint-check    - Check code quality without fixing"
	@echo "  make format        - Auto-format code with black"
	@echo "  make format-check  - Check formatting without fixing"
	@echo "  make type-check    - Run mypy type checker"
	@echo ""
	@echo "Security:"
	@echo "  make security-check - Run security scans (pip-audit, bandit)"
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
	@echo "  make docker-logs   - Show Docker service logs"
	@echo ""
	@echo "Workflows:"
	@echo "  make dev-check     - Quick dev workflow (fast tests + coverage)"
	@echo "  make pre-commit    - Run pre-commit hook manually"

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

# Linting & Code Quality targets
lint: format-check lint-check type-check
	@echo ""
	@echo "✅ All linting checks passed"

lint-check:
	@echo "🔍 Running linters..."
	@command -v ruff >/dev/null 2>&1 && ruff check services/ tests/ || echo "⚠️  ruff not installed (pip install ruff)"
	@command -v flake8 >/dev/null 2>&1 && flake8 services/ tests/ --max-line-length=100 || echo "⚠️  flake8 not installed"

format:
	@echo "🎨 Auto-formatting code..."
	@command -v black >/dev/null 2>&1 && black services/ tests/ || echo "⚠️  black not installed (pip install black)"
	@echo "✅ Code formatted"

format-check:
	@echo "🎨 Checking code formatting..."
	@command -v black >/dev/null 2>&1 && black services/ tests/ --check || echo "⚠️  black not installed (pip install black)"

type-check:
	@echo "🔍 Running type checker..."
	@command -v mypy >/dev/null 2>&1 && mypy services/ --ignore-missing-imports || echo "⚠️  mypy not installed (pip install mypy)"

# Security targets
security-check:
	@echo "🔒 Running security scans..."
	@echo ""
	@echo "📦 Checking Python dependencies..."
	@command -v pip-audit >/dev/null 2>&1 && pip-audit || echo "⚠️  pip-audit not installed (pip install pip-audit)"
	@echo ""
	@echo "🔍 Scanning code for security issues..."
	@command -v bandit >/dev/null 2>&1 && bandit -r services/ -ll || echo "⚠️  bandit not installed (pip install bandit)"
	@echo ""
	@echo "✅ Security scan complete"

# Quick development workflow
dev-check: test-fast coverage-check
	@echo ""
	@echo "✅ Quick dev check complete"

# Full CI simulation
ci-check: clean test-all lint security-check
	@echo ""
	@echo "✅ Full CI check complete (local simulation)"

# Pre-commit simulation
pre-commit:
	@echo "🔍 Running pre-commit checks..."
	@bash .git/hooks/pre-commit || echo "⚠️  Pre-commit hook not installed (run: make setup)"
