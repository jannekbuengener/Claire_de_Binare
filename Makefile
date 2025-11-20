# Makefile für Claire de Binaire Test-Suite
# Unterstützt sowohl CI (schnell, Mocks) als auch lokale E2E-Tests

.PHONY: help test test-unit test-integration test-e2e test-local test-full-system test-coverage test-services test-integration-local test-all-local docker-up docker-down docker-health clean install-dev

help:
	@echo "Claire de Binaire - Test Commands"
	@echo ""
	@echo "CI-Tests (schnell, mit Mocks):"
	@echo "  make test              - Alle CI-Tests (unit + integration)"
	@echo "  make test-unit         - Nur Unit-Tests"
	@echo "  make test-integration  - Nur Integration-Tests (mit Mocks)"
	@echo "  make test-coverage     - Tests mit Coverage-Report"
	@echo ""
	@echo "Lokale E2E-Tests (mit echten Containern):"
	@echo "  make test-e2e          - Alle E2E-Tests"
	@echo "  make test-local        - Alle local-only Tests"
	@echo "  make test-full-system  - Komplett: docker-compose up + E2E"
	@echo ""
	@echo "Erweiterte Lokale Tests:"
	@echo "  make test-services     - Service-spezifische Tests (Signal, Risk, Execution)"
	@echo "  make test-integration-local - Service-Integration-Tests"
	@echo "  make test-all-local    - Alle lokalen Tests (E2E + Services + Integration)"
	@echo ""
	@echo "Docker-Hilfsfunktionen:"
	@echo "  make docker-up         - Starte alle Container"
	@echo "  make docker-down       - Stoppe alle Container"
	@echo "  make docker-health     - Prüfe Health-Status aller Container"

# ============================================================================
# CI-Tests (schnell, mit Mocks)
# ============================================================================

test: test-unit test-integration
	@echo "✅ Alle CI-Tests erfolgreich"

test-unit:
	@echo "🧪 Führe Unit-Tests aus..."
	pytest -v -m unit

test-integration:
	@echo "🔌 Führe Integration-Tests aus (mit Mocks)..."
	pytest -v -m "integration and not e2e and not local_only"

test-coverage:
	@echo "📊 Führe Tests mit Coverage-Report aus..."
	pytest --cov=services --cov=backoffice/services --cov-report=html --cov-report=term -m "not e2e and not local_only"
	@echo "📄 Coverage-Report: htmlcov/index.html"

# ============================================================================
# Lokale E2E-Tests (mit echten Containern)
# ============================================================================

test-e2e:
	@echo "🚀 Führe E2E-Tests aus (benötigt laufende Container)..."
	@echo "⚠️  Stelle sicher, dass 'docker compose up -d' läuft!"
	pytest -v -m e2e

test-local:
	@echo "🏠 Führe local-only Tests aus..."
	@echo "⚠️  Stelle sicher, dass 'docker compose up -d' läuft!"
	pytest -v -m local_only

test-full-system: docker-up docker-health test-e2e
	@echo "✅ Vollständiger System-Test erfolgreich"

# ============================================================================
# Erweiterte Lokale Tests (tests/local/)
# ============================================================================

test-services:
	@echo "🔧 Führe Service-Tests aus (Signal Engine, Risk Manager, Execution)..."
	@echo "⚠️  Benötigt: docker compose up -d"
	pytest -v -m local_only tests/local/service/

test-integration-local:
	@echo "🔗 Führe Service-Integration-Tests aus..."
	@echo "⚠️  Benötigt: Alle Services running (cdb_core, cdb_risk, cdb_execution)"
	pytest -v -m local_only tests/local/integration/

test-all-local: docker-up docker-health
	@echo "🚀 Führe ALLE lokalen Tests aus (E2E + Services + Integration)..."
	pytest -v -m local_only tests/e2e/ tests/local/
	@echo "✅ Alle lokalen Tests abgeschlossen"

# ============================================================================
# Docker-Hilfsfunktionen
# ============================================================================

docker-up:
	@echo "🐳 Starte Docker Compose Stack..."
	docker compose up -d
	@echo "⏳ Warte 10s bis Container hochgefahren sind..."
	sleep 10

docker-down:
	@echo "🛑 Stoppe Docker Compose Stack..."
	docker compose down

docker-health:
	@echo "🏥 Prüfe Health-Status aller Container..."
	@docker compose ps | grep -E "(cdb_redis|cdb_postgres|cdb_ws|cdb_core|cdb_risk|cdb_execution)" || true
	@echo ""
	@echo "Health-Check Details:"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep cdb_ || true

# ============================================================================
# Zusätzliche Hilfsfunktionen
# ============================================================================

clean:
	@echo "🧹 Räume Test-Artefakte auf..."
	rm -rf .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

install-dev:
	@echo "📦 Installiere Development-Dependencies..."
	pip install -r requirements-dev.txt
