# Makefile für Claire de Binaire Test-Suite
# Unterstützt sowohl CI (schnell, Mocks) als auch lokale E2E-Tests

.PHONY: help test test-unit test-integration test-e2e test-local test-local-stress test-local-performance test-local-lifecycle test-full-system test-coverage docker-up docker-down docker-health

help:
	@echo "Claire de Binaire - Test Commands"
	@echo ""
	@echo "CI-Tests (schnell, mit Mocks):"
	@echo "  make test                    - Alle CI-Tests (unit + integration)"
	@echo "  make test-unit               - Nur Unit-Tests"
	@echo "  make test-integration        - Nur Integration-Tests (mit Mocks)"
	@echo "  make test-coverage           - Tests mit Coverage-Report"
	@echo ""
	@echo "Lokale E2E-Tests (mit echten Containern):"
	@echo "  make test-e2e                - Alle E2E-Tests (18 Tests)"
	@echo "  make test-local              - Alle local-only Tests"
	@echo "  make test-local-stress       - Stress-Tests (100+ Events)"
	@echo "  make test-local-performance  - Performance-Tests (Query-Speed)"
	@echo "  make test-local-lifecycle    - Docker Lifecycle-Tests (DESTRUKTIV!)"
	@echo "  make test-full-system        - Komplett: Docker + E2E + Local"
	@echo ""
	@echo "Docker-Hilfsfunktionen:"
	@echo "  make docker-up               - Starte alle Container"
	@echo "  make docker-down             - Stoppe alle Container"
	@echo "  make docker-health           - Prüfe Health-Status aller Container"

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

test-local-stress:
	@echo "🔥 Führe Stress-Tests aus (100+ Events)..."
	@echo "⚠️  Ressourcenintensiv - kann bis zu 60s dauern!"
	pytest -v -m "local_only and slow" tests/local/test_full_system_stress.py

test-local-performance:
	@echo "⚡ Führe Performance-Tests aus (Analytics Queries)..."
	pytest -v -m local_only tests/local/test_analytics_performance.py

test-local-lifecycle:
	@echo "🔄 Führe Docker Lifecycle-Tests aus..."
	@echo "⚠️  DESTRUKTIV - Container werden neu gestartet!"
	pytest -v -m local_only tests/local/test_docker_lifecycle.py -s

test-full-system: docker-up docker-health test-e2e test-local
	@echo "✅ Vollständiger System-Test erfolgreich (E2E + Local)"

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
