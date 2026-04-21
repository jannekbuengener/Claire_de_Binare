# ---
# relations:
#   role: build_automation
#   domain: orchestration
#   upstream:
#     - docker-compose.yml
#     - pytest.ini
#     - infrastructure/scripts/systemcheck.py
#     - infrastructure/scripts/daily_check.py
#     - infrastructure/scripts/backup_all.ps1
#   downstream: []
#   invariants:
#     - docker must be installed and in PATH.
#     - pytest must be installed.
# ---
# Makefile für Claire de Binare Test-Suite
# Unterstützt sowohl CI (schnell, Mocks) als auch lokale E2E-Tests
# 431B note: the canonical Docker CI lab baseline is infrastructure/compose/base.yml + infrastructure/compose/test.yml.
# This Makefile remains focused on local/runtime-oriented operator flows and does not define that baseline.

MCP_CONFIG_PATHS ?=
REPLAY_INPUT_CANDLES ?=
REPLAY_OUTPUT_DIR ?= artifacts/replay_reports
REPLAY_STRATEGY_ID ?= primary_breakout_v1
REPLAY_SYMBOL ?= BTCUSDT
REPLAY_ADAPTER_ID ?= primary_breakout_runner_v1
REPLAY_DRY_RUN ?= 0
REPLAY_DETERMINISTIC_VERIFY ?= 1

.PHONY: help test test-unit test-integration test-e2e test-local test-local-stress test-local-performance test-local-lifecycle test-local-cli test-local-chaos test-local-backup test-full-system test-coverage docker-up docker-down docker-health systemcheck daily-check backup backup-postgres-only restore backup-health paper-trading-start paper-trading-logs paper-trading-stop replay-shadow-run rollback cleanup mcp-config-validate security-scan pre-close

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
	@echo "  make backup                  - Konsolidiertes Backup (Postgres + Redis)"
	@echo "  make backup-postgres-only    - Legacy PostgreSQL-only Backup"
	@echo "  make restore                 - Restore aus F:\\Claire_Backups"
	@echo "  make backup-health           - Backup-Aktualitaet pruefen"
	@echo ""
	@echo "Session-Close:"
	@echo "  make pre-close               - Pre-close sweep: prueft untracked Artefakte in kanonischen Pfaden"
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
	@echo "⚠️  Stelle sicher, dass der Stack laeuft: make docker-up"
	pytest -v -m e2e

test-local:
	@echo "🏠 Führe local-only Tests aus..."
	@echo "⚠️  Stelle sicher, dass der Stack laeuft: make docker-up"
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
	@echo "🐳 Starte Docker Compose Stack (BLUE+RED)..."
	@pwsh -NoProfile -Command "docker network create cdb_network 2>&1 | Out-Null; Write-Host '✓ cdb_network bereit'"
	@pwsh -NoProfile -Command "if (-not $$env:SECRETS_PATH) { $$env:SECRETS_PATH = Join-Path $$env:USERPROFILE 'Documents\.secrets\.cdb' }; if (-not (Test-Path $$env:SECRETS_PATH)) { Write-Error ('SECRETS_PATH not found: ' + $$env:SECRETS_PATH); exit 1 }; docker compose -f 'infrastructure/compose/compose.blue.yml' up -d"
	@pwsh -NoProfile -Command "if (-not $$env:SECRETS_PATH) { $$env:SECRETS_PATH = Join-Path $$env:USERPROFILE 'Documents\.secrets\.cdb' }; docker compose -f 'infrastructure/compose/compose.red.yml' up -d"
	@pwsh -NoProfile -Command "Start-Sleep -Seconds 10"
else
docker-up:
	@echo "🐳 Starte Docker Compose Stack (BLUE+RED)..."
	@docker network create cdb_network 2>/dev/null || true
	@export SECRETS_PATH=$${SECRETS_PATH:-$$HOME/Documents/.secrets/.cdb}; \
	 [ -d "$$SECRETS_PATH" ] || { echo "ERROR: SECRETS_PATH not found: $$SECRETS_PATH" >&2; exit 1; }; \
	 docker compose -f infrastructure/compose/compose.blue.yml up -d; \
	 docker compose -f infrastructure/compose/compose.red.yml up -d
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
	@echo "🛑 Stoppe Docker Compose Stack (BLUE+RED)..."
	docker compose -f infrastructure/compose/compose.red.yml down; \
	docker compose -f infrastructure/compose/compose.blue.yml down

docker-health:
	@echo "🏥 Prüfe Health-Status aller Container (BLUE+RED)..."
	@echo "--- BLUE ---"
	@docker compose -f infrastructure/compose/compose.blue.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | grep cdb_ || true
	@echo "--- RED ---"
	@docker compose -f infrastructure/compose/compose.red.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | grep cdb_ || true

# ============================================================================
# Paper Trading (14-Tage Test)
# ============================================================================

pre-close:
	@bash scripts/pre_close_sweep.sh

systemcheck:
	@echo "🔍 Führe Pre-Flight-Checks aus..."
	python infrastructure/scripts/systemcheck.py

daily-check:
	@echo "📊 Führe täglichen Gesundheitscheck aus..."
	python infrastructure/scripts/daily_check.py

backup:
	@echo "💾 Führe konsolidiertes Backup aus (Postgres + Redis)..."
	powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/backup_all.ps1

backup-postgres-only:
	@echo "💾 Führe PostgreSQL-only Backup aus (Legacy)..."
	powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/backup_postgres.ps1

restore:
	@echo "🔄 Restore aus F:\\Claire_Backups (interaktiv)..."
	powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/restore_all.ps1

backup-health:
	@echo "🏥 Prüfe Backup-Aktualität..."
	powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/backup_health_check.ps1

paper-trading-start: systemcheck
	@echo "🚀 Starte Paper Trading Runner..."
	@echo "⚠️  Stelle sicher, dass alle anderen Container laufen: make docker-up"
	@if [ "$${SIGNAL_STRATEGY_ID:-primary_breakout_v1}" != "primary_breakout_v1" ]; then echo "Error: SIGNAL_STRATEGY_ID must be primary_breakout_v1 for the paper path"; exit 1; fi
	@if [ "$${SIGNAL_ADAPTER_ID:-momentum_builtin}" != "momentum_builtin" ]; then echo "Error: SIGNAL_ADAPTER_ID must be momentum_builtin for the current main adapter path"; exit 1; fi
	@if [ "$${SIGNAL_TRADE_SIDE_MODE:-long_only}" != "long_only" ]; then echo "Error: SIGNAL_TRADE_SIDE_MODE must be long_only for primary_breakout_v1"; exit 1; fi
	docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_paper_runner
	@echo ""
	@echo "✅ Paper Trading Runner gestartet!"
	@echo "   Logs anzeigen: make paper-trading-logs"
	@echo "   Health-Check: curl http://localhost:8004/health"
	@echo "   Grafana: http://localhost:3000"

paper-trading-logs:
	@echo "📜 Paper Trading Logs (Ctrl+C zum Beenden)..."
	docker compose -f infrastructure/compose/compose.blue.yml logs -f cdb_paper_runner

paper-trading-stop:
	@echo "🛑 Stoppe Paper Trading Runner..."
	docker compose -f infrastructure/compose/compose.blue.yml stop cdb_paper_runner
	@echo "✅ Paper Trading Runner gestoppt"

ifeq ($(OS),Windows_NT)
replay-shadow-run:
	@pwsh -NoProfile -Command "$$input='$(REPLAY_INPUT_CANDLES)'; if ([string]::IsNullOrWhiteSpace($$input)) { Write-Error 'REPLAY_INPUT_CANDLES is required'; Write-Host 'Usage: make replay-shadow-run REPLAY_INPUT_CANDLES=<candles.json|candles.jsonl> [REPLAY_OUTPUT_DIR=artifacts/replay_reports]'; exit 1 }; if (-not (Test-Path $$input)) { Write-Error ('input candles file not found: ' + $$input); exit 1 }; $$out='$(REPLAY_OUTPUT_DIR)'; New-Item -ItemType Directory -Force -Path $$out | Out-Null; $$args=@('-m','services.validation.strategy_replay_runner','--input-candles',$$input,'--output-dir',$$out,'--strategy-id','$(REPLAY_STRATEGY_ID)','--symbol','$(REPLAY_SYMBOL)','--adapter-id','$(REPLAY_ADAPTER_ID)'); if ('$(REPLAY_DRY_RUN)' -eq '1') { $$args += '--dry-run' }; if ('$(REPLAY_DETERMINISTIC_VERIFY)' -eq '1') { $$args += '--deterministic-verify' }; Write-Host '▶ replay-shadow-run'; Write-Host ('  input_candles=' + $$input); Write-Host ('  output_dir=' + $$out); Write-Host '  strategy_id=$(REPLAY_STRATEGY_ID) symbol=$(REPLAY_SYMBOL) adapter_id=$(REPLAY_ADAPTER_ID)'; Write-Host '  dry_run=$(REPLAY_DRY_RUN) deterministic_verify=$(REPLAY_DETERMINISTIC_VERIFY)'; & python @args; $$rc=$$LASTEXITCODE; if ($$rc -eq 0) { Write-Host '✅ replay-shadow-run completed (bundle_dir is printed by the runner)' } else { Write-Error ('replay-shadow-run failed with exit code ' + $$rc) }; exit $$rc"
else
replay-shadow-run:
	@if [ -z "$(REPLAY_INPUT_CANDLES)" ]; then \
		echo "ERROR: REPLAY_INPUT_CANDLES is required"; \
		echo "Usage: make replay-shadow-run REPLAY_INPUT_CANDLES=<candles.json|candles.jsonl> [REPLAY_OUTPUT_DIR=artifacts/replay_reports]"; \
		exit 1; \
	fi
	@if [ ! -f "$(REPLAY_INPUT_CANDLES)" ]; then \
		echo "ERROR: input candles file not found: $(REPLAY_INPUT_CANDLES)"; \
		exit 1; \
	fi
	@mkdir -p "$(REPLAY_OUTPUT_DIR)"
	@dry_flag=""; \
	if [ "$(REPLAY_DRY_RUN)" = "1" ]; then dry_flag="--dry-run"; fi; \
	det_flag=""; \
	if [ "$(REPLAY_DETERMINISTIC_VERIFY)" = "1" ]; then det_flag="--deterministic-verify"; fi; \
	echo "▶ replay-shadow-run"; \
	echo "  input_candles=$(REPLAY_INPUT_CANDLES)"; \
	echo "  output_dir=$(REPLAY_OUTPUT_DIR)"; \
	echo "  strategy_id=$(REPLAY_STRATEGY_ID) symbol=$(REPLAY_SYMBOL) adapter_id=$(REPLAY_ADAPTER_ID)"; \
	echo "  dry_run=$(REPLAY_DRY_RUN) deterministic_verify=$(REPLAY_DETERMINISTIC_VERIFY)"; \
	python -m services.validation.strategy_replay_runner \
		--input-candles "$(REPLAY_INPUT_CANDLES)" \
		--output-dir "$(REPLAY_OUTPUT_DIR)" \
		--strategy-id "$(REPLAY_STRATEGY_ID)" \
		--symbol "$(REPLAY_SYMBOL)" \
		--adapter-id "$(REPLAY_ADAPTER_ID)" \
		$$dry_flag \
		$$det_flag; \
	rc=$$?; \
	if [ $$rc -eq 0 ]; then \
		echo "✅ replay-shadow-run completed (bundle_dir is printed by the runner)"; \
	else \
		echo "❌ replay-shadow-run failed with exit code $$rc" >&2; \
	fi; \
	exit $$rc
endif

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
	@echo "🔎 Validiere MCP-Konfiguration..."
	python tools/validate_mcp_config.py $(MCP_CONFIG_PATHS)

# ============================================================================
# Security Scanning
# ============================================================================

security-scan:
	@echo "🛡️  Führe Security-Scan aus..."
	@if command -v gitleaks > /dev/null; then \
		gitleaks detect --source . -v; \
	else \
		echo "⚠️  gitleaks nicht installiert, überspringe secret scanning"; \
	fi
	@ruff check .
	@bandit -r core/ services/
