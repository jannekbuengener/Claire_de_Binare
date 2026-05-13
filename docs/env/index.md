# Env Index

Kurzer operativer Index fuer Toggles, Secrets, Defaults und ihre primaeren Consumer.
Nicht exhaustiv; diese Seite zeigt die Canon-Pointer.

## Betriebsrelevante Schalter

| Variable / Config | Default | Primaere Consumer | Canon-Pointer |
|-------|-------|-------|-------|
| `TRADING_MODE` | `paper` | Trading-Mode-Auswahl, Execution-Logging | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) |
| `LIVE_TRADING_CONFIRMED` | unset | Human gate fuer `TRADING_MODE=live` | [`core/config/trading_mode.py`](../../core/config/trading_mode.py) |
| `MOCK_TRADING` | `true` | Execution-Service waehlt Non-Live statt Live-Executor | [`services/execution/config.py`](../../services/execution/config.py), [`services/execution/service.py`](../../services/execution/service.py) |
| `MOCK_EXECUTION_MODE` | `simple` | Opt-in fuer expliziten Mock-Pfad: `simple`=`MockExecutor`, `simulator`=`SimulatorExecutor` | [`services/execution/config.py`](../../services/execution/config.py), [`services/execution/service.py`](../../services/execution/service.py), [`services/execution/simulator_executor.py`](../../services/execution/simulator_executor.py) |
| `SIMULATOR_ORDER_BOOK_DEPTH` / `SIMULATOR_VOLATILITY` | `1000000` / `0.02` | Tuning fuer den market-like, nicht-live Simulator-Pfad | [`services/execution/config.py`](../../services/execution/config.py), [`services/execution/simulator_executor.py`](../../services/execution/simulator_executor.py) |
| `CDB_CONTROL_BOARD_AUTOMATION_ENABLED` | `false` | Control-Board-Routing und Upsert | [docs/runbooks/control_board_board_as_code.md](../runbooks/control_board_board_as_code.md) |
| `POSTGRES_SSLMODE` | `prefer` | Postgres-DSN / SSL-Verbindung | [`core/utils/postgres_client.py`](../../core/utils/postgres_client.py), [`infrastructure/tls/TLS_SETUP.md`](../../infrastructure/tls/TLS_SETUP.md) |
| `SECRETS_PATH` | lokal: `~/Documents/.secrets/.cdb`, CI: `${{ github.workspace }}/.ci-secrets` | Compose, Bootstrap, E2E/Soak | BLUE+RED compose (`compose.blue.yml` / `compose.red.yml`), [`infrastructure/scripts/bootstrap_local.sh`](../../infrastructure/scripts/bootstrap_local.sh), [tests/fixtures/README.md](../../tests/fixtures/README.md) |
| `CDB_EXTERNAL_TESTS` | off | Opt-in fuer externe Integrations-Tests | [`tests/integration/test_mexc_testnet.py`](../../tests/integration/test_mexc_testnet.py) |
| `surrealdb_enabled` / `governance_source` | `false` / `git` | SurrealDB-Mirror und Governance-Read-Quelle | [`infrastructure/config/surrealdb/feature-flags.yaml`](../../infrastructure/config/surrealdb/feature-flags.yaml), [docs/surrealdb/rollback-cutover-plan.md](../surrealdb/rollback-cutover-plan.md) |

Safety-Hinweis: `MOCK_EXECUTION_MODE=simulator` wird nur beachtet, wenn `MOCK_TRADING=true` ist. Der Pfad bleibt explizit non-live und schaltet keinen echten Exchange-Zugriff frei.

## GitHub-Automation Secrets

Diese Secrets steuern vor allem Board-, Milestone- und Weekly-Digest-Automation:

- `ADD_TO_PROJECT_PAT`
- `CDB_GH_APP_ID`
- `CDB_GH_APP_PRIVATE_KEY`
- `CDB_GH_APP_INSTALLATION_ID`
- `CDB_PR_AUTOMATION_TOKEN`

Canon-Pointer:

- [docs/runbooks/project_board_automation.md](../runbooks/project_board_automation.md)
- [docs/runbooks/control_board_board_as_code.md](../runbooks/control_board_board_as_code.md)

## Lokale Secret Stores und Runner-Env

- Lokale Secret-Verwaltung:
  - [`infrastructure/scripts/manage_secrets.ps1`](../../infrastructure/scripts/manage_secrets.ps1)
  - [`infrastructure/scripts/init-secrets.ps1`](../../infrastructure/scripts/init-secrets.ps1)
  - [`infrastructure/scripts/check_env.ps1`](../../infrastructure/scripts/check_env.ps1)
- Self-hosted Runner Env:
  - [`infrastructure/actions-runner/.env.runner.example`](../../infrastructure/actions-runner/.env.runner.example)

## Read-only DB discovery secrets

For later Agent-/MCP-readonly discovery, prefer a dedicated DSN secret name:

- `POSTGRES_READONLY_PASSWORD_DSN` - preferred DSN name for a dedicated readonly
  login such as `cdb_readonly`
- `POSTGRES_READONLY_PASSWORD` - optional raw password secret if the operator
  path keeps password and DSN separately

Guardrails:

- Secret values stay outside the repo in the canonical secret store.
- Runtime-service credentials such as `claire_user` / `POSTGRES_PASSWORD` are
  not acceptable for Agent-/MCP-discovery.
- The canonical readonly-login boundary is documented in
  [`docs/runbooks/postgres_least_privilege_rls.md`](../runbooks/postgres_least_privilege_rls.md).

## Wenn du etwas nachschlagen willst

- Defaults und Validierung fuer lokale Laufzeit: [`infrastructure/scripts/check_env.ps1`](../../infrastructure/scripts/check_env.ps1)
- DB-Verbindungsvariablen und TLS: [`core/utils/postgres_client.py`](../../core/utils/postgres_client.py)
- Fixture-DB-Zugang fuer Tests: [tests/fixtures/README.md](../../tests/fixtures/README.md)
- Board-/Project-v2-Auth und Fallbacks: [docs/runbooks/project_board_automation.md](../runbooks/project_board_automation.md)
