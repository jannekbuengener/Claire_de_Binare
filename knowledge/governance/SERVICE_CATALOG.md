# SERVICE_CATALOG.md - Vollständige Service-Inventarisierung

**Erstellt:** 2025-12-28
**Verantwortlich:** Claude (Session Lead)
**Prüfintervall:** Bei jedem Stack-Start, mindestens wöchentlich

---

## Status-Definitionen

| Status | Bedeutung |
|--------|-----------|
| **AKTIV** | Service läuft in Production/Dev Stack (compose.blue.yml oder compose.red.yml) |
| **OVERLAY** | Service in separatem Compose-Overlay (z.B. logging.yml), nicht Teil des Standard-BLUE/RED-Starts |
| **BEREIT** | Code vollständig, Dockerfile vorhanden, Compose deaktiviert |
| **GEPLANT** | Architektur definiert, Implementierung ausstehend |
| **LEGACY** | Deprecated, wird nicht mehr verwendet |
| **GAP** | Diskrepanz zwischen Code und Deployment |

---

## Navigation READMEs (Working Repo)

Docs-only operator indices from PRs #2999, #3001, #3003. Ersetzen keine kanonische Funktionsbeschreibung in den Tabellen unten.

| Bereich | README |
|---|---|
| Service-Index | [`services/README.md`](../../services/README.md) |
| Shared core | [`core/README.md`](../../core/README.md) |
| Replay / contracts | [`core/replay/README.md`](../../core/replay/README.md), [`core/contracts/README.md`](../../core/contracts/README.md) |
| Offline validation | [`services/validation/README.md`](../../services/validation/README.md) |
| DB schema / migrations | [`docs/db/index.md`](../../docs/db/index.md) |
| Paper runner (compose `cdb_paper_runner`) | [`tools/paper_trading/README.md`](../../tools/paper_trading/README.md) — **nicht** `services/paper_runner/` |

---

## Applikations-Services

### BLUE Stack (compose.blue.yml) — Core, always-on

| Service | Container | Port | Code | README | Status | Funktion |
|---------|-----------|------|------|--------|--------|----------|
| **Market** | cdb_market | 8009 | services/market/ | [README](../../services/market/README.md) | **AKTIV** | market_state:{symbol} Owner (Issue #1201); parallel market-state update logic; stimulus_fixture wall-clock override for RC_004 safety (PR #3019); Redis retry/reconnect, /health fail-closed |
| **Candles** | cdb_candles | 8007 | services/candles/ | [README](../../services/candles/README.md) | **AKTIV** | Tick→1-min Aggregation; implements stimulus_fixture wall-clock override in market-state update to preserve freshness for RC_004 (PR #3022) |
| **Regime** | cdb_regime | 8008 | services/regime/ | [README](../../services/regime/README.md) | **AKTIV** | ADX/ATR Regime Classification |
| **Allocation** | cdb_allocation | 8006 | services/allocation/ | [README](../../services/allocation/README.md) | **AKTIV** | Regime→Allocation Mapping |
| **Risk** | cdb_risk | 8002 | services/risk/ | [README](../../services/risk/README.md) | **AKTIV** | Risk Gate, Circuit Breaker, Kill-Switch; `/kill-switch` Fehlerantworten fail-closed ohne Exception-Details |
| **Execution** | cdb_execution | 8003 | services/execution/ | [README](../../services/execution/README.md) | **AKTIV** | Order Execution (MOCK_TRADING=true default); `/orders` Fehlerantworten nur mit sicherem Fehlercode |
| **DB Writer** | cdb_db_writer | — | services/db_writer/ | [README](../../services/db_writer/README.md) | **AKTIV** | Redis→PostgreSQL Persistenz; `db_writer.py` schreibt `stream.candles_1m` in `candles_1m` (Postgres), `candle_normalizer.py` normalisiert die Stream-Payloads auf dem Write-Pfad (PR #1856) |
| **Paper Runner** | cdb_paper_runner | 8004 | tools/paper_trading/ | [README](../../tools/paper_trading/README.md) | **AKTIV** | Paper Trading Orchestrator |

### RED Stack (compose.red.yml) — Signal + Monitoring, failure-isolated from BLUE

| Service | Container | Port | Code | README | Status | Funktion |
|---------|-----------|------|------|--------|--------|----------|
| **WebSocket** | cdb_ws | 8000 | services/ws/ | [README](../../services/ws/README.md) | **AKTIV** | MEXC Market Data Stream (protobuf); `MexcV3Client` wird nur bei `WS_SOURCE=mexc_pb` lazy geladen (Health-/Metrics-Surface bleibt importierbar ohne websocket-spezifische Dependency); `decoded_messages_total` und `decode_errors_total` werden via Delta-Logik aus absoluten Client-Werten als Prometheus Counter fortgeschrieben |
| **Signal** | cdb_signal | 8005 (Runtime) | services/signal/ | [README](../../services/signal/README.md) | **AKTIV** | Signal Generation (`primary_breakout_v1` default nutzt zeitbasierte Lookback-Semantik, `momentum_builtin` statische Adapter-Grenze); audit metadata: `config_snapshot` (deterministic runtime params snapshot) + `config_hash` (full SHA-256); `SIGNAL_BOT_ID` environment variable wired via compose.red.yml (PR #2129) liefert Experiment-Kontext im SIGNAL-Payload, aber keine neue first-class Ledger-ID; `source=stimulus_fixture` + `stimulus_run_id` erzeugen deterministische `signal_id`s fuer exportierbare paper chains; reserved metadata keys (strategy_id, bot_id, config_snapshot, config_hash, signal_reason, signal_inputs) sind immutable und können nicht durch Candidate-Signal-Metadata überschrieben werden |
| **Reports** | cdb_reports | — | services/reports/ | — | **AKTIV** | Daily Order Summary + Email |

Hinweis: Der Config-Default fuer `SIGNAL_PORT` liegt in `services/signal/config.py` bei `8001`; im kanonischen RED-Runtime-Pfad wird fuer `cdb_signal` in `infrastructure/compose/compose.red.yml` explizit `SIGNAL_PORT=8005` gesetzt. Ebenso wird `SIGNAL_BOT_ID` (audit identity) explizit via `environment:` durchgereicht (PR #2129).

---

## Core Libraries (nicht runtime-services)

### Replay Infrastructure (LR-021, PR #1808)

**Pfad:** `core/replay/`, `services/validation/` (reporter + CLI)

**Navigation:** [`core/replay/README.md`](../../core/replay/README.md), [`core/contracts/README.md`](../../core/contracts/README.md), [`services/validation/README.md`](../../services/validation/README.md)

**Funktion:** Deterministic shadow replay stack für accelerated backtesting, validation und gate evaluation offline, ohne live/paper/Redis-Runtime-Integration; ARVP §4.2 datasets via `DatasetSpec` + `DatasetProvider` (FileBackedDatasetProvider für JSON/JSONL, DBBackedDatasetProvider für Postgres `candles_1m`).

| Module/Component | Code-Pfad | Status | Beschreibung |
|---|---|---|---|
| **Replay Contracts** | `core/replay/replay_contracts.py` | **AKTIV** (PR #1808) | Frozen dataclasses für deterministic input/output tracking |
| **Replay Determinism** | `core/replay/determinism.py` | **AKTIV** (PR #1808) | Canonical JSON hashing, integrity verification |
| **Replay Clock Context** | `core/replay/clock_context.py` | **AKTIV** (PR #1808) | Deterministic, wall-clock-free time handling |
| **Replay Execution** | `core/replay/execution.py` | **AKTIV** (PR #1808) | Envelope chain emission, order/fill wrapping |
| **Deterministic Loop** | `core/replay/deterministic_loop.py` | **AKTIV** (PR #1808) | Tick-by-tick replay orchestration mit integrity gate |
| **Envelopes** | `core/replay/envelopes.py` | **AKTIV** (PR #1808) | Decision/Order/Fill envelope types + replay metadata |
| **Dataset Spec** | `core/replay/dataset_spec.py` | **AKTIV** (PR #1856) | Immutable request spec für historische Replay-Datasets (ARVP §4.2). Frozen fields: `source` (file\|db), `file_path` (file mode), `db_dataset_window` (db mode: START_TS_MS:END_TS_MS). Fingerprint via canonical_hash. Fail-closed validation: mutually exclusive source fields. |
| **Dataset Provider** | `core/replay/dataset_provider.py` | **AKTIV** (PR #1856, PR #1891) | FileBackedDatasetProvider (JSON/JSONL) + DBBackedDatasetProvider (candles_1m Postgres). Operator-facing API: `--dataset-source file\|db`, `--input-candles FILE` (file mode), `--db-dataset-window START_TS_MS:END_TS_MS` (db mode). Beide validieren Ordering, 1m-Takt, erforderliche Felder (ts_ms, high, low, close). ARVP §4.2 data-shape layer (regime_id/window boundary enforcement gehört zum Bridge/Runner). |
| **Replay Scheduler** | `core/replay/scheduler.py` | **AKTIV** (PR #1859) | Event-time replay scheduler mit deterministischen Speed-Profilen, Warmup/Live-Split und fail-closed Boundary-Validation |
| **Shadow Comparison** | `core/replay/shadow_compare.py` | **AKTIV** (PR #1914) | Deterministic, offline comparison of replay output windows against explicit paper-trading reference windows (no DB/Redis). Pure function; fail-closed on misalignment. Decimal-quantized rate values (no-float rule). Deterministic fingerprinting via canonical_hash. |
| **Replay vs Paper Compare** | `core/replay/replay_vs_paper_compare.py` | **AKTIV** (PR #1914) | Glue layer: consumes replay_report.v1 (report.json) + arvp_paper_reference_window.v1 (paper reference); produces shadow_comparison.json + shadow_comparison_summary.md. Deterministic; explicit reject data handling; fail-closed on missing inputs. |
| **ARVP Gate** | `core/replay/arvp_gate.py` | **AKTIV** (PR #1914) | Machine-readable verdict surface: aggregates replay/comparison/scenario/regime artifacts into pass/fail/blocked verdict with explicit blocking vs informational rule classification. Pure function; deterministic fingerprinting. |
| **Simulator Calibration Report** | `core/replay/simulator_calibration_report.py` | **AKTIV** (PR #1916) | Consumes shadow_comparison.json; produces simulator_calibration_report.json + simulator_calibration_summary.md with simulator drift classification (optimistic/pessimistic/ambiguous/unusable). Deterministic; explicit fill_rate_delta handling; proxy-only inferred signals when explicit data absent. Reporting only; no simulator mutation. |
| **ARVP Regime Scorecards** | `core/replay/arvp_regime_scorecards.py` | **AKTIV** (PR #1918) | Regime-segmented reading surface for replay + comparison outputs. Deterministic; explicit on missing regime context (status: ok/unavailable/insufficient-data). Supports replay-side regime trace + optional comparison regime breakdown. Reporting only, no policy semantics. |
| **Paper Reference Window Export** | `core/replay/paper_reference_window_export.py` | **AKTIV** (PR #1920, PR #2949) | Export comparison-grade paper_reference_window from correlation_ledger (append-only audit trail). Fail-closed on missing/invalid fields; deterministic ordering by (timestamp_ms, event_pk). Requires ≥1 ORDER + ≥1 FILL with paper_-prefix. Contract version: arvp_paper_reference_window.v1. `order_id` bleibt der kanonische interne Ledger-Bezug; `exchange_order_id` wird nur als Payload-Kontext geführt, wenn er vom kanonischen Wert abweicht. `bot_id`/`config_hash` dienen als SIGNAL-anchor-/payload-abgeleiteter Queryability-Kontext, nicht als neue first-class Ledger-ID. |
| **Replay Reporter** | `services/validation/replay_reporter.py` | **AKTIV** (PR #1808) | Artifact bundle writer (report.json, manifest.json, audit.log) |
| **Backtest Runner** | `services/validation/strategy_backtest_runner.py` | **AKTIV** (PR #1944) | Deterministische `primary_breakout_v1` Backtest-Fläche. Implementiert opt-in Gate-Trace via `gate_trace_path` (JSONL) zur Entscheidung-Auditierung; Diagnose-/Auditfläche, keine Trading-Policy. |
| **ARVP Replay CLI** | `services/validation/strategy_replay_runner.py` | **AKTIV** (PR #1808, PR #1859, PR #1891, PR #1944) | Operator-facing entry-point: `run_arvp_replay()` → `main()`. Validates fail-closed: `--dataset-source` (file\|db), `--speedup-profile`, scheduler metadata. Exponiert `--gate-trace-path` und reicht diesen an den Backtest-Runner weiter. Source-aware baseline + scenario-group paths. Exit Codes 0/1/2 (success/validation/runtime). Config: ARVPReplayConfig mit dataset/strategy/adapter/scheduler params. |
| **Compare CLI Runner** | `services/validation/replay_vs_paper_compare_runner.py` | **AKTIV** (PR #1914) | Operator-facing CLI (`--replay-report FILE --paper-reference FILE --output-dir DIR`). Produces shadow_comparison artifacts. Exit codes: 0 aligned / 1 usage error / 2 parse/unusable. |
| **Calibration Report CLI** | `services/validation/simulator_calibration_report_runner.py` | **AKTIV** (PR #1916) | Operator-facing CLI (`--comparison shadow_comparison.json --output-dir DIR`). Produces simulator_calibration_report.json + simulator_calibration_summary.md. Exit codes: 0 aligned / 1 usage error / 2 parse/unusable. |
| **Regime Scorecard CLI** | `services/validation/arvp_regime_scorecard_runner.py` | **AKTIV** (PR #1918) | Operator-facing CLI (`--run-id ID --replay-trace FILE --comparison FILE --output-dir DIR`). Optional inputs; fail-closed on invalid JSON. Produces arvp_regime_scorecard.json + arvp_regime_scorecard_summary.md. Exit codes: 0 ok / 1 usage / 2 parse error. |
| **Paper Reference Window CLI** | `services/validation/paper_reference_window_runner.py` | **AKTIV** (PR #1920, PR #2133, PR #2479) | Operator-facing CLI (`--strategy-id ID --symbol SYM --start-ts-ms TS --end-ts-ms TS --output FILE`). Reads correlation_ledger from Postgres via required `POSTGRES_READONLY_PASSWORD_DSN`; fail-closed validation requires `current_user=session_user=cdb_readonly`, effective `SELECT` on `public.correlation_ledger`, and rejects any `INSERT`/`UPDATE`/`DELETE` privilege drift before export. Produces arvp_paper_reference_window.v1 JSON. Fail-closed validation: requires ≥1 ORDER + ≥1 FILL mit paper_-prefix. Signal audit context (`bot_id`, `config_hash`) wird durch PR #2133 Exporter Guards als SIGNAL-anchor-/payload-abgeleiteter Queryability-Kontext zur Chain-Validierung herangezogen; keine neue first-class Experiment-ID. Exit codes: 0 success / 1 usage / 2 DB/contract error. |
| **Paper Runtime Stimulus CLI** | `services/validation/paper_runtime_stimulus_runner.py` | **AKTIV** (PR #2989, PR #2992, PR #3006, PR #3016, PR #3019, PR #3022) | Runtime-adjacent operator CLI for ARVP paper-window production (#2968/#2969). Produces deterministic `stimulus_run_id` -> `signal_id` chains (PR #3016). Enforces wall-clock aligned `last_tick_ts_ms` for `stimulus_fixture` events to satisfy RC_004 freshness guards (PRs #3019, #3022). Safety preflight REQUIRED. No DB writes; LR NO-GO. |

**Interne Abhängigkeiten:** Nutzen `core/replay/canonical_json.py` (deterministic serialization), `core/replay/envelopes.py` (envelope tracking).

**Externe Abhängigkeiten:** `core/domain/` (models, events), `core/clients/` (MEXC API), `core/indicators/` (technical indicators), `core/contracts/` (decision contracts).

**Tests:** 453 unit tests (core/replay/ + services/validation/ replay-specific tests), alle grün.

---

## Infrastruktur-Services

### BLUE Stack (compose.blue.yml)

| Service | Container | Image | Port | Status | Funktion |
|---------|-----------|-------|------|--------|----------|
| **PostgreSQL** | cdb_postgres | postgres:15.17-alpine | 5432 | **AKTIV** | Persistenz |
| **Redis** | cdb_redis | redis:7.4.8-alpine | 6379 | **AKTIV** | Cache, Pub/Sub, Streams |

### RED Stack (compose.red.yml) — Monitoring

| Service | Container | Image | Port | Status | Funktion |
|---------|-----------|-------|------|--------|----------|
| **Prometheus** | cdb_prometheus | prom/prometheus:v3.11.3 | 19090→9090 | **AKTIV** | Metrics Collection |
| **Grafana** | cdb_grafana | grafana/grafana:12.4.3-security-02-ubuntu@sha256:089f9dbb | 3000 | **AKTIV** | Dashboards |
| **Postgres Exporter** | cdb_postgres_exporter | prometheuscommunity/postgres-exporter | 9187 | **AKTIV** | PG Metrics; DSN-Wiring ueber `postgres_password` Secret + `PGPASSWORD`, `DATA_SOURCE_NAME` wird zur Laufzeit aus `POSTGRES_USER`/`POSTGRES_DB` und Host/Port zusammengesetzt |
| **Redis Exporter** | cdb_redis_exporter | bitnami/redis-exporter | 9121 | **AKTIV** | Redis Metrics |
| **cAdvisor** | cdb_cadvisor | gcr.io/cadvisor/cadvisor:v0.49.2 | — | **AKTIV** | Container Metrics |

### Logging Overlay (logging.yml) — separates Overlay, nicht Teil des Standard-BLUE/RED-Starts

Aktivierung: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/logging.yml up -d`

| Service | Container | Image | Status | Funktion |
|---------|-----------|-------|--------|----------|
| **Loki** | cdb_loki | grafana/loki:2.9.3 | **OVERLAY** | Log Aggregation |
| **Promtail** | cdb_promtail | grafana/promtail:2.9.3 | **OVERLAY** | Log Shipping |
| **Alertmanager** | cdb_alertmanager | prom/alertmanager:v0.27.0 | **OVERLAY** | Alert Routing + Email |

---

## Test-Services (test.yml)

| Service | Container | Zweck |
|---------|-----------|-------|
| cdb_redis_test | Redis für Tests | Isolierte Test-DB |
| cdb_postgres_test | PostgreSQL für Tests | Isolierte Test-DB |
| cdb_risk_test | Risk Service Test | Integration Tests |
| cdb_execution_test | Execution Service Test | Integration Tests |
| cdb_test_runner | pytest Container | Test Orchestration |

---

## GAP-Analyse

### Aktuell keine kritischen GAPs

Alle Services aus compose.blue.yml und compose.red.yml sind AKTIV und vollständig konfiguriert.

### Historisch (behoben)

- **2025-12-28:** Signal Service war als `cdb_core` fehlbenannt → umbenannt zu `cdb_signal` (Port 8005)
- **~März 2026:** allocation, regime, market waren in dev.yml auskommentiert → in compose.blue.yml aktiv mit Env-Vars und Healthchecks
- **~März 2026:** BLUE/RED-Split eingeführt → base.yml/dev.yml-Kette durch compose.blue.yml + compose.red.yml ersetzt

---

## Compose-Architektur (kanonisch seit BLUE/RED-Split)

```
compose.blue.yml   → BLUE: Data Layer + Control Layer + Core Trading  [kanonisch]
compose.red.yml    → RED: Signal Generation + Monitoring               [kanonisch]
logging.yml        → Logging Overlay (Loki + Promtail + Alertmanager)  [separates Overlay, nicht Standard-Start]
```

Legacy-Layer (base.yml, dev.yml, tls.yml, etc.) existieren noch im Repo, sind aber nicht mehr kanonisch für den Betrieb.

---

## Stack-Start Befehl (kanonisch)

```bash
# Netzwerk (einmalig)
docker network create cdb_network

# BLUE + RED starten
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# PowerShell Front Door
.\tools\cdb.ps1 runtime up
```

---

## Stack-Verification (kanonisch)

| Pfad | Erwartung | Hinweis |
|------|-----------|---------|
| `tools/verify_stack.ps1` | 10 Services (BLUE+RED-Subset) | Default `$IncludeLogging = $false`; Loki/Promtail leben in `logging.yml`, nicht im Standard-Start |
| `tools/verify_stack.ps1 -IncludeLogging:$true` | +2 OVERLAY-Services | Nur wenn `logging.yml`-Overlay aktiv ist |
| `.\tools\cdb.ps1 stack verify` | Front Door zu `verify_stack.ps1` | Gleiche Semantik wie oben |
| `make docker-health` | Container-Health via Makefile | Windows-kompatibel (PowerShell `Select-String`, kein `grep`) |

Referenz: `infrastructure/compose/SERVICE_MAPPING.md`, PR #2670.

## Prüf-Checkliste (bei jedem Stack-Start)

- [ ] Alle AKTIV-Services laufen (`docker ps`)
- [ ] Alle Services "healthy" (keine "unhealthy" oder "starting")
- [ ] `tools/verify_stack.ps1` oder `make docker-health` ohne unerwartete Missing/Unhealthy
- [ ] OVERLAY-Services (Loki/Promtail) nur geprueft, wenn Overlay bewusst gestartet (`-IncludeLogging:$true`)
- [ ] GAP-Services bewusst nicht gestartet (dokumentiert)
- [ ] BEREIT-Services bewusst deaktiviert (Begründung aktuell)
- [ ] Keine unbekannten Container im Stack

---

## Änderungshistorie

| Datum | Änderung | Durch |
|-------|----------|-------|
| 2025-12-28 | Initiale Erstellung nach Governance-Review | Claude |
| 2025-12-28 | GAP identifiziert: Signal Service fehlt in Compose | Claude |
| 2025-12-28 | Signal Service aktiviert: cdb_core → cdb_signal (Port 8005) | Claude |
| 2026-03-29 | BLUE/RED-Split reconciliation: market/candles/regime/allocation→AKTIV, Exporter/Reports/Alertmanager ergänzt, Image-Versionen aktualisiert, Compose-Referenzen auf compose.blue/red.yml (#1302) | Claude |
| 2026-04-01 | Logging Overlay: Status AKTIV→OVERLAY für Loki/Promtail/Alertmanager; Status-Definition OVERLAY ergänzt; Aktivierungsbefehl explizit; Compose-Architektur-Notation präzisiert (#1409) | Claude |
| 2026-04-11 | Signal-Port-Semantik präzisiert: Config-Default `SIGNAL_PORT=8001`, kanonischer Runtime-Port `8005` via `compose.red.yml` | Codex |
| 2026-04-11 | Signal/Risk Runtime-Drift bereinigt: Signal-Strategie-/Stream-Semantik und Risk-Input-/Metric-Semantik auf current-main präzisiert | Codex |
| 2026-04-18 | PR #1752 Nachzug: Market Email-Alerter-Init ohne Empfaenger-Klartext-Logging in Katalogfunktion nachgezogen | Codex |
| 2026-04-18 | PR #1755 Nachzug: Risk-/Execution-Fehlerantworten und Kill-Switch-Fallback auf stacktrace-freie Fehlercodes/Safemessages dokumentiert | Codex |
| 2026-04-19 | Prometheus-Image-Version nachgezogen: v3.10.0 → v3.11.2 (PR #1767, Issue #1771); enger Katalog-Nachzug gegen current-main | Codex |
| 2026-04-20 | PR #1808 Nachzug: LR-021 deterministic replay infrastructure (core/replay/ + services/validation/) als Core Libraries dokumentiert; 6 Modules + 2 Components + 453 Tests (Issue #1809) | Codex |
| 2026-04-22 | PR #1856 Nachzug: ARVP §4.2 DatasetSpec + DatasetProvider (FileBackedDatasetProvider + DBBackedDatasetProvider) in Core Libraries ergänzt; DB-Writer Candle-Persistence (candle_normalizer.py → candles_1m) nachgezogen (Issue #1857) | Codex |
| 2026-04-22 | PR #1859 Nachzug: `core/replay/scheduler.py` und minimaler Replay-CLI-Scheduler-Pfad (`speedup_profile`, `dataset_summary["scheduler"]`) im Replay-Katalog ergänzt (Issue #1860) | Codex |
| 2026-04-23 | PR #1891 Nachzug: ARVP Finalization – Dataset Layer (file\|db operator-facing front-door, db_dataset_window format, source-aware paths), CLI naming (run_arvp_replay canonical), legacy code removed, fail-closed validation finalized. DatasetSpec/DatasetProvider erweiterte Beschreibungen (Issue #1892) | Codex |
| 2026-04-24 | PRs #1914/#1916/#1918/#1920 Nachzug: ARVP validation comparisons & scorecards. shadow_compare, replay_vs_paper_compare, ARVP gate, simulator_calibration_report, arvp_regime_scorecards, paper_reference_window_export + CLI-Runner dokumentiert. Offline-Validation und Audit-Komponenten, keine Runtime-Services im BLUE/RED-Stack. (Issues #1915/#1917/#1919/#1921) | Codex |
| 2026-04-26 | PRs #1944/#1947 Nachzug: `primary_breakout_v1` nutzt zeitbasierte Lookback-Semantik (SignalEngine). `strategy_backtest_runner` implementiert opt-in Gate-Trace (JSONL); ARVP Replay CLI exponiert/forwarded `--gate-trace-path`. (Issues #1945/#1948) | Codex |
| 2026-05-13 | PR #2453/#2455 Nachzug: WS-Service (Delta-Counter + lazy `mexc_pb`-Import) und Postgres-Exporter-DSN/Secret-Wiring im RED-Stack nachgezogen (Issues #2454/#2456) | Codex |
| 2026-05-29 | PR #2670/#2671 Nachzug: Stack-Verification-Tabelle (`verify_stack.ps1` Default ohne Logging-Overlay, `-IncludeLogging:$true` opt-in, Windows-`make docker-health`) ergänzt (Issue #2671) | Codex |
| 2026-06-05 | PRs #2989/#2992/#3006 Nachzug: `paper_runtime_stimulus_runner.py` als runtime-adjacent ARVP operator CLI im Validation-Katalog ergänzt; `source=stimulus_fixture` + `stimulus_run_id` machen `cdb_signal`-IDs fuer paper chains deterministisch (Issues #2990/#2993/#3008) | Codex |
| 2026-06-05 | PRs #2999/#3001/#3003 Nachzug: § Navigation READMEs + README-Spalte; Paper Runner Code `tools/paper_trading/` explizit; Replay/DB README-Links (Issues #3000/#3004) | Cursor |
| 2026-06-06 | PRs #3016/#3019/#3022 Nachzug: Stimulus-Determinismus und Wall-Clock-Override für Freshness (RC_004) in Market & Candles dokumentiert (Issues #3017/#3020/#3023) | Codex |
## PostgreSQL Schema Artefacts

| Artefakt | Migration | Status | Bedeutung |
|---|---|---|---|
| `risk_events` idempotency | `infrastructure/database/migrations/005_risk_events_idempotent.sql` | **AKTIV** | `decision_pk` + `input_snapshot_hash`; Unique-Key auf `decision_pk` macht Risk-Persistenz replay-sicher. |
| `correlation_ledger` | `infrastructure/database/migrations/006_correlation_phase8c.sql` | **AKTIV** | Append-only Audit-Trail fuer `SIGNAL`/`DECISION`/`ORDER`/`FILL`-Ketten; Grundlage fuer Export- und Replay-Referenzfenster. |
| `blocked_decisions` | `infrastructure/database/migrations/006_correlation_phase8c.sql` | **AKTIV** | Append-only Audit-Trail fuer BLOCK-Entscheidungen; nutzt denselben `decision_pk`-Mechanismus wie `risk_events`. |
