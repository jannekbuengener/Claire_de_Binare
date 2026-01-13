# ---
# relations:
#   role: build_automation
#   domain: orchestration
#   upstream:
#     - docker-compose.yml
#     - pytest.ini
#     - infrastructure/scripts/systemcheck.py
#     - infrastructure/scripts/daily_check.py
#     - infrastructure/scripts/backup_postgres.ps1
#   downstream: []
#   invariants:
#     - docker must be installed and in PATH.
#     - pytest must be installed.
# ---
# Makefile für Claire de Binare Test-Suite
# Unterstützt sowohl CI (schnell, Mocks) als auch lokale E2E-Tests

.PHONY: help test test-unit test-integration test-e2e test-local test-local-stress test-local-performance test-local-lifecycle test-local-cli test-local-chaos test-local-backup test-full-system test-coverage docker-up docker-down docker-health systemcheck daily-check backup paper-trading-start paper-trading-logs paper-trading-stop rollback cleanup

help:
	@echo "Claire de Binare - Test Commands"
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
	@echo "  make test-local-cli          - CLI-Tools Tests (query_analytics.py)"
	@echo "  make test-local-chaos        - Chaos/Resilience Tests (SEHR DESTRUKTIV!)"
	@echo "  make test-local-backup       - Backup & Recovery Tests (pg_dump/restore)"
	@echo "  make test-full-system        - Komplett: Docker + E2E + Local"
	@echo ""
	@echo "Docker-Hilfsfunktionen:"
	@echo "  make docker-up               - Starte alle Container (Dev-Mode)"
	@echo "  make docker-up-prod          - Starte alle Container (Prod-Mode)"
	@echo "  make docker-down             - Stoppe alle Container"
	@echo "  make docker-health           - Prüfe Health-Status aller Container"
	@echo ""
	@echo "Paper Trading (14-Tage Test):"
	@echo "  make systemcheck             - Pre-Flight-Checks vor Start"
	@echo "  make paper-trading-start     - Starte Paper Trading Runner"
	@echo "  make paper-trading-logs      - Zeige Paper Trading Logs (live)"
	@echo "  make paper-trading-stop      - Stoppe Paper Trading Runner"
	@echo "  make daily-check             - Täglicher Gesundheitscheck"
	@echo "  make backup                  - PostgreSQL Backup (manuell)"
	@echo ""
	@echo "Repo-Hygiene & Rollback:"
	@echo "  make rollback MR=<number>    - Rollback eines Merge Requests"
	@echo "  make cleanup                 - Aufräumen merged Branches (DRY-RUN)"
	@echo "  make cleanup-live            - Aufräumen merged Branches (LIVE)"

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
	pytest --cov=core --cov=services --cov=infrastructure/scripts --cov-report=html --cov-report=term --cov-fail-under=80 -m "not e2e and not local_only"
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

test-local-cli:
	@echo "🛠️  Führe CLI-Tools Tests aus..."
	@echo "⚠️  Benötigt PostgreSQL mit Daten!"
	pytest -v -m local_only tests/local/test_cli_tools.py -s

test-local-chaos:
	@echo "💥 Führe Chaos/Resilience Tests aus..."
	@echo "⚠️  SEHR DESTRUKTIV - Container werden ge-killed!"
	@echo "⚠️  Nur ausführen wenn System stabil ist!"
	pytest -v -m "local_only and chaos" tests/local/test_chaos_resilience.py -s

test-local-backup:
	@echo "💾 Führe Backup & Recovery Tests aus..."
	@echo "⚠️  Testet pg_dump/pg_restore Workflows!"
	pytest -v -m local_only tests/local/test_backup_recovery.py -s

test-full-system: docker-up docker-health test-e2e test-local
	@echo "✅ Vollständiger System-Test erfolgreich (E2E + Local)"

# ============================================================================
# Docker-Hilfsfunktionen
# ============================================================================

ifeq ($(OS),Windows_NT)
docker-up:
	@echo "🐳 Starte Docker Compose Stack..."
	@pwsh -NoProfile -Command "if (Test-Path 'infrastructure/compose/base.yml') { Write-Host '✓ Using Compose Fragments (base + dev)'; docker compose -f 'infrastructure/compose/base.yml' -f 'infrastructure/compose/dev.yml' up -d } else { Write-Host '⚠️  Fallback to legacy docker-compose.yml'; docker compose up -d }"
	@pwsh -NoProfile -Command "Start-Sleep -Seconds 10"
else
docker-up:
	@echo "🐳 Starte Docker Compose Stack..."
	@if [ -f infrastructure/compose/base.yml ]; then \
		echo "✓ Using Compose Fragments (base + dev)"; \
		docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d; \
	else \
		echo "⚠️  Fallback to legacy docker-compose.yml"; \
		docker compose up -d; \
	fi
	@echo "⏳ Warte 10s bis Container hochgefahren sind..."
	sleep 10
endif

docker-up-prod:
	@echo "🐳 Starte Docker Compose Stack (PRODUCTION)..."
	@if [ -f infrastructure/compose/base.yml ]; then \
		echo "✓ Using Compose Fragments (base + prod)"; \
		docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/prod.yml up -d; \
	else \
		echo "❌ Error: Prod mode requires Compose Fragments"; \
		exit 1; \
	fi
	@echo "⏳ Warte 10s bis Container hochgefahren sind..."
	sleep 10

docker-down:
	@echo "🛑 Stoppe Docker Compose Stack..."
	@if [ -f infrastructure/compose/base.yml ]; then \
		docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml down; \
	else \
		docker compose down; \
	fi

docker-health:
	@echo "🏥 Prüfe Health-Status aller Container..."
	@docker compose ps | grep -E "(cdb_redis|cdb_postgres|cdb_ws|cdb_core|cdb_risk|cdb_execution)" || true
	@echo ""
	@echo "Health-Check Details:"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep cdb_ || true

# ============================================================================
# Paper Trading (14-Tage Test)
# ============================================================================

systemcheck:
	@echo "🔍 Führe Pre-Flight-Checks aus..."
	python infrastructure/scripts/systemcheck.py

daily-check:
	@echo "📊 Führe täglichen Gesundheitscheck aus..."
	python infrastructure/scripts/daily_check.py

backup:
	@echo "💾 Führe PostgreSQL Backup aus..."
	powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/backup_postgres.ps1

paper-trading-start: systemcheck
	@echo "🚀 Starte Paper Trading Runner..."
	@echo "⚠️  Stelle sicher, dass alle anderen Container laufen: make docker-up"
	docker compose up -d cdb_paper_runner
	@echo ""
	@echo "✅ Paper Trading Runner gestartet!"
	@echo "   Logs anzeigen: make paper-trading-logs"
	@echo "   Health-Check: curl http://localhost:8004/health"
	@echo "   Grafana: http://localhost:3000"

paper-trading-logs:
	@echo "📜 Paper Trading Logs (Ctrl+C zum Beenden)..."
	docker compose logs -f cdb_paper_runner

paper-trading-stop:
	@echo "🛑 Stoppe Paper Trading Runner..."
	docker compose stop cdb_paper_runner
	@echo "✅ Paper Trading Runner gestoppt"

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

# ============================================================================
# Repo-Hygiene & Rollback (PR-02)
# ============================================================================

rollback:
ifndef MR
	@echo "Error: MR parameter required"
	@echo "Usage: make rollback MR=<number>"
	@echo "Example: make rollback MR=88"
	@exit 1
endif
	@echo "🔄 Rolling back MR #$(MR)..."
	@bash scripts/rollback_pr.sh $(MR)

cleanup:
	@echo "🧹 Cleanup merged branches (DRY-RUN)..."
	@DRY_RUN=true bash scripts/cleanup_branches.sh 30

cleanup-live:
	@echo "⚠️  Cleanup merged branches (LIVE)..."
	@DRY_RUN=false bash scripts/cleanup_branches.sh 30

# ============================================================================
# MCP Config Validation
# ============================================================================

mcp-config-validate:
	@echo "🔎 Validiere mcp-config.toml..."
	python tools/validate_mcp_config.py
