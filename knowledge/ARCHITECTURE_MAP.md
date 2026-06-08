# ARCHITECTURE_MAP - Claire de Binare

**Version:** 1.0
**Erstellt:** 2025-12-28
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

---

## 1. System Overview

Claire de Binare ist ein **event-getriebenes Krypto-Trading-System** mit:
- Redis Pub/Sub fuer Inter-Service-Kommunikation
- PostgreSQL fuer Event-Persistenz
- Docker Compose fuer Orchestrierung
- Paper Trading als Default-Modus (Live Trading erfordert explizites Gate)

**Operatives Inventar:** `governance/SERVICE_CATALOG.md` (Working Repo)

**Operator READMEs (Working Repo, docs-only navigation):** [`../services/README.md`](../services/README.md), [`../core/README.md`](../core/README.md), [`../infrastructure/database/README.md`](../infrastructure/database/README.md), [`../tools/paper_trading/README.md`](../tools/paper_trading/README.md). Vollstaendige README-Index-Tabelle: `governance/SERVICE_CATALOG.md` § Navigation READMEs.

---

## 2. Service Map (SOLL)

### Core Pipeline
```
[Market] --> [WS] --> [Signal] --> [Risk] --> [Execution]
   |           |          |          |            |
   v           v          v          v            v
             Redis     Redis      Redis        Redis
             pub/sub   pub/sub    pub/sub      pub/sub
                                    |            |
                                    +-----<------+
                                    (order_results)
                                          |
                                          v
                                    [DB Writer] --> [PostgreSQL]
```

### BLUE Stack (compose.blue.yml) — Core, always-on

| Service | Container | Port | Code | Operator README |
|---------|-----------|------|------|-----------------|
| PostgreSQL | cdb_postgres | 5432 | infrastructure/database/ | [database/README.md](../infrastructure/database/README.md) |
| Redis | cdb_redis | 6379 | infrastructure/compose/ | [compose/README.md](../infrastructure/compose/README.md) |
| Market | cdb_market | 8009 | services/market/ | [services/market/README.md](../services/market/README.md) |
| Candles | cdb_candles | 8007 | services/candles/ | [services/candles/README.md](../services/candles/README.md) |
| Regime | cdb_regime | 8008 | services/regime/ | [services/regime/README.md](../services/regime/README.md) |
| Allocation | cdb_allocation | 8006 | services/allocation/ | [services/allocation/README.md](../services/allocation/README.md) |
| Risk | cdb_risk | 8002 | services/risk/ | [services/risk/README.md](../services/risk/README.md) |
| Execution | cdb_execution | 8003 | services/execution/ | [services/execution/README.md](../services/execution/README.md) |
| DB Writer | cdb_db_writer | — | services/db_writer/ | [services/db_writer/README.md](../services/db_writer/README.md) |
| Paper Runner | cdb_paper_runner | 8004 | tools/paper_trading/ | [tools/paper_trading/README.md](../tools/paper_trading/README.md) |

### RED Stack (compose.red.yml) — Signal + Monitoring, failure-isolated

| Service | Container | Port | Code | Operator README |
|---------|-----------|------|------|-----------------|
| WebSocket | cdb_ws | 8000 | services/ws/ | [services/ws/README.md](../services/ws/README.md) |
| Signal | cdb_signal | 8005 (Runtime) | services/signal/ | [services/signal/README.md](../services/signal/README.md) |
| Reports | cdb_reports | — | services/reports/ | — |

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| Prometheus | cdb_prometheus | 19090→9090 | Metrics |
| Grafana | cdb_grafana | 3000 | Dashboards |
| Postgres Exporter | cdb_postgres_exporter | 9187 | PG Metrics; liest `postgres_password` als Secret, setzt `PGPASSWORD` und baut `DATA_SOURCE_NAME` aus `POSTGRES_USER`/`POSTGRES_DB` + Host/Port |
| Redis Exporter | cdb_redis_exporter | 9121 | Redis Metrics |
| cAdvisor | cdb_cadvisor | — | Container Metrics |

Hinweis: `services/signal/config.py` hat `SIGNAL_PORT`-Default `8001`; der kanonische Runtime-Port ist `8005`, weil `infrastructure/compose/compose.red.yml` fuer `cdb_signal` `SIGNAL_PORT=8005` setzt.

### Logging Overlay (logging.yml) — separates Overlay, nicht Teil des Standard-BLUE/RED-Starts

Aktivierung: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/logging.yml up -d`

| Service | Container | Compose-Datei |
|---------|-----------|---------------|
| Loki | cdb_loki | logging.yml |
| Promtail | cdb_promtail | logging.yml |
| Alertmanager | cdb_alertmanager | logging.yml |

---

## 3. Runtime Reality (IST)

### Verification Command
```bash
# Kanonischer Start
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Oder via PowerShell
.\tools\cdb.ps1 runtime up

# Schnellcheck
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"

# Kanonischer Stack-Verify (10 Services, BLUE+RED-Subset; Logging-Overlay standardmaessig aus)
pwsh -NoProfile -File tools/verify_stack.ps1
# Optional mit Loki/Promtail, wenn logging.yml laeuft:
pwsh -NoProfile -File tools/verify_stack.ps1 -IncludeLogging:$true
# Front Door:
.\tools\cdb.ps1 stack verify

# Makefile-Health (Windows-kompatibel via PowerShell-Filter statt grep)
make docker-health
```

### Erwarteter Output (BLUE + RED healthy)
```
cdb_postgres          Up (healthy)
cdb_redis             Up (healthy)
cdb_market            Up (healthy)
cdb_candles           Up (healthy)
cdb_regime            Up (healthy)
cdb_allocation        Up (healthy)
cdb_risk              Up
cdb_execution         Up
cdb_db_writer         Up (healthy)
cdb_paper_runner      Up (healthy)
cdb_ws                Up (healthy)
cdb_signal            Up (healthy)
cdb_prometheus        Up (healthy)
cdb_grafana           Up (healthy)
cdb_postgres_exporter Up (healthy)
cdb_redis_exporter    Up (healthy)
cdb_cadvisor          Up
cdb_reports           Up (healthy)
```

---

## 4. Key Dataflows

### Redis Channels
| Channel | Publisher | Subscriber(s) |
|---------|-----------|---------------|
| market_data | cdb_ws | cdb_market, cdb_candles, cdb_signal, cdb_paper_runner |
| signals | cdb_signal | cdb_risk, cdb_db_writer |
| orders | cdb_risk | cdb_execution, cdb_db_writer |
| order_results | cdb_execution | cdb_risk, cdb_db_writer |
| alerts | cdb_risk | — (kein verifizierter Subscriber; Fire-and-forget) |
| portfolio_snapshots | cdb_paper_runner | cdb_db_writer |

### Event Types
- `SIGNAL_GENERATED` - Handelssignal erzeugt
- `ORDER_PLACED` - Order an Exchange gesendet
- `POSITION_OPENED` - Position eroeffnet

---

## 5. Core Libraries (nicht runtime-services, sondern shared infrastruktur)

### Replay Infrastructure (LR-021, PR #1808)

| Module | File | Funktion | Status |
|--------|------|----------|--------|
| **Replay Contracts** | `core/replay/replay_contracts.py` | Frozen dataclasses für Replay-Input/Output; determinism envelope tracking | **AKTIV** (PR #1808) |
| **Replay Determinism** | `core/replay/determinism.py` | Canonical JSON hashing, integrity verification, error validation | **AKTIV** (PR #1808) |
| **Replay Clock Context** | `core/replay/clock_context.py` | Deterministic, wall-clock-free time handling für replay events | **AKTIV** (PR #1808) |
| **Replay Execution** | `core/replay/execution.py` | Envelope chain emission, order/fill wrapping für replay runs | **AKTIV** (PR #1808) |
| **Deterministic Loop** | `core/replay/deterministic_loop.py` | Tick-by-tick replay orchestration mit integrity gate | **AKTIV** (PR #1808) |
| **Envelopes** | `core/replay/envelopes.py` | Decision/Order/Fill envelope types + replay metadata fields | **AKTIV** (PR #1808) |
| **Dataset Spec** | `core/replay/dataset_spec.py` | Frozen request-spec für historische Replay-Datasets (ARVP §4.2); Fingerprint via canonical_hash | **AKTIV** (PR #1856) |
| **Dataset Provider** | `core/replay/dataset_provider.py` | FileBackedDatasetProvider (JSON/JSONL) + DBBackedDatasetProvider (candles_1m Postgres); ARVP §4.2 | **AKTIV** (PR #1856) |
| **Historical Bridge** | `core/replay/historical_bridge.py` | File-backed historical input adapter for `primary_breakout_v1`; supports configurable `price_policy` parameter for replay-vs-live signal evaluation | **AKTIV** (PR #3081) |
| **Replay Scheduler** | `core/replay/scheduler.py` | Event-time replay scheduler mit deterministischen Speed-Profilen, Warmup/Live-Split und fail-closed Boundary-Validation | **AKTIV** (PR #1859) |

**Nutzung:** Shadow replay (accelerated backtesting, validation, gate evaluation offline) ohne live/paper/Redis-Runtime-Integration; ARVP §4.2 datasets via `DatasetSpec` + `DatasetProvider` (FileBackedDatasetProvider für JSON/JSONL, DBBackedDatasetProvider für Postgres `candles_1m`).

**Operator-Facing Dataset Layer (ARVP §4.2):**
- **Dataset Source**: `--dataset-source file|db` (default: `file`)
- **File Mode**: `--input-candles FILE` (JSON array oder JSONL)
- **DB Mode**: `--db-dataset-window START_TS_MS:END_TS_MS` (Explicit window label aus Postgres `candles_1m`)
- **Fail-Closed**: Beide Quellen validieren Ordering, 1-Minute-Takt, erforderliche Felder. Mutually-exclusive: `source='file'` XOR `source='db'`.
- **Source-Aware Paths**: Baseline und scenario-group Workflows unterstützen beide Dataset-Quellen.

**Reporter & CLI:**
| Component | File | Funktion | Status |
|-----------|------|----------|--------|
| **Replay Reporter** | `services/validation/replay_reporter.py` | Deterministic artifact bundle writer (report.json, manifest.json, audit.log) | **AKTIV** (PR #1808) |
| **Backtest Runner** | `services/validation/strategy_backtest_runner.py` | Deterministische `primary_breakout_v1` Backtest-Fläche. Implementiert opt-in Gate-Trace (`gate_trace_path`) für JSONL-Entscheidungsprotokollierung; kein Standard-Output ohne Opt-in; kein Trace im zweiten Determinismus-Pass. | **AKTIV** (PR #1944) |
| **ARVP Replay CLI** | `services/validation/strategy_replay_runner.py` | Operator-facing entry-point (`run_arvp_replay()` → `main()`). Fail-closed: validates `--dataset-source` (file\|db), `--speedup-profile`, scheduler metadata. Exponiert `--gate-trace-path` und reicht diesen an den Backtest-Runner weiter. Exit Codes 0/1/2. Source-aware baseline + scenario-group paths. | **AKTIV** (PR #1808, PR #1859, PR #1891, PR #1944) |
| **Shadow Comparison** | `core/replay/shadow_compare.py` | Deterministic, offline comparison of replay output windows against explicit paper-trading reference windows. Pure function; fail-closed on misalignment. Decimal-quantized rate values. | **AKTIV** (PR #1914) |
| **Replay vs Paper Compare** | `core/replay/replay_vs_paper_compare.py` | Glue layer consuming replay_report.v1 + arvp_paper_reference_window.v1; produces shadow_comparison.json + shadow_comparison_summary.md. Deterministic; explicit reject data handling; fail-closed on missing inputs. | **AKTIV** (PR #1914) |
| **Compare CLI Runner** | `services/validation/replay_vs_paper_compare_runner.py` | Operator-facing CLI (`--replay-report FILE --paper-reference FILE --output-dir DIR`). Produces shadow_comparison artifacts. Exit codes: 0 aligned / 1 usage error / 2 parse/unusable. | **AKTIV** (PR #1914) |
| **ARVP Gate** | `core/replay/arvp_gate.py` | Machine-readable verdict surface: aggregates replay/comparison/scenario/regime artifacts into pass/fail/blocked verdict with explicit blocking vs informational rule classification. Deterministic fingerprinting. | **AKTIV** (PR #1914) |
| **Simulator Calibration Report** | `core/replay/simulator_calibration_report.py` | Consumes shadow_comparison.json; produces simulator_calibration_report.json + simulator_calibration_summary.md with drift classification (optimistic/pessimistic/ambiguous/unusable). Deterministic; explicit fill_rate_delta handling. | **AKTIV** (PR #1916) |
| **Calibration Report CLI** | `services/validation/simulator_calibration_report_runner.py` | Operator-facing CLI (`--comparison shadow_comparison.json --output-dir DIR`). Exit codes: 0 aligned / 1 usage error / 2 parse/unusable. | **AKTIV** (PR #1916) |
| **ARVP Regime Scorecards** | `core/replay/arvp_regime_scorecards.py` | Regime-segmented reading surface for replay + comparison outputs. Deterministic; explicit on missing regime context (status: ok/unavailable/insufficient-data). Reporting only, no policy semantics. | **AKTIV** (PR #1918) |
| **Regime Scorecard CLI** | `services/validation/arvp_regime_scorecard_runner.py` | Operator-facing CLI (`--run-id ID --replay-trace FILE --comparison FILE --output-dir DIR`). Optional inputs; fail-closed on invalid JSON. Produces arvp_regime_scorecard.json + arvp_regime_scorecard_summary.md. Exit codes: 0 ok / 1 usage / 2 parse error. | **AKTIV** (PR #1918) |
| **Paper Reference Window Export** | `core/replay/paper_reference_window_export.py` | Export comparison-grade paper_reference_window from correlation_ledger. Fail-closed on missing/invalid fields; deterministic ordering by (timestamp_ms, event_pk). Requires ≥1 ORDER + ≥1 FILL with paper_-prefix. `order_id` bleibt der kanonische interne Ledger-Bezug; `exchange_order_id` wird nur als Payload-Kontext geführt, wenn er vom kanonischen Wert abweicht. `bot_id`/`config_hash` werden als SIGNAL-anchor-/payload-abgeleiteter Queryability-Kontext genutzt, nicht als neue first-class Ledger-IDs. | **AKTIV** (PR #1920, PR #2949) |
| **Paper Reference Window CLI** | `services/validation/paper_reference_window_runner.py` | Operator-facing CLI (`--strategy-id ID --symbol SYM --start-ts-ms TS --end-ts-ms TS --output FILE`). Reads correlation_ledger from Postgres via required `POSTGRES_READONLY_PASSWORD_DSN`; fail-closed unless `current_user` and `session_user` both resolve to `cdb_readonly`, effective `SELECT` on `public.correlation_ledger` is present, and any `INSERT`/`UPDATE`/`DELETE` privilege drift is rejected. Produces arvp_paper_reference_window.v1 JSON. Exit codes: 0 success / 1 usage / 2 DB/contract error. Optionale `--bot-id`/`--config-hash` Filter qualifizieren ueber SIGNAL-Anker, fuehren aber keine neue first-class Experiment-ID ein. | **AKTIV** (PR #1920, PR #2479) |
| **Paper Runtime Stimulus CLI** | `services/validation/paper_runtime_stimulus_runner.py` | Runtime-adjacent operator CLI: publishes a canonical BTCUSDT 1m breakout fixture to Redis `market_data` (default `--dry-run-preview`; `--publish` only after safety preflight `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true`). Supports `--runtime-relative` / `--base-ts-ms` to shift fixture timestamps to current wall-clock aligned to 1m cadence while preserving breakout shape (PR #2992). For `source=stimulus_fixture`, `stimulus_run_id` now seeds deterministic `signal_id` generation in `services/signal/service.py`, and services (`cdb_market`, `cdb_candles`) now enforce wall-clock aligned `last_tick_ts_ms` to satisfy RC_004 freshness guards in `cdb_risk` (PRs #3016, #3019, #3022). No DB writes; no Live-Go. Intended to help produce comparison-grade `paper_` chains for #2968/#2969. Exit codes: 0 success / 1 usage / 2 safety or publish failure. | **AKTIV** (PR #2989, PR #2992, PR #3006, PR #3016, PR #3019, PR #3022) |
| **Price Policy Evaluation CLI** | `tools/replay/evaluate_price_policies.py` | Operator-facing CLI for `price_policy` evaluation against replay report. Produces price-policy-evaluation JSON + summary evidence; consumes `report.json` from a replay run. Used for #3079 price-policy gap analysis. Exit codes: 0 success / 1 usage error. | **AKTIV** (PR #3081) |

---

## 6. Strategic Service Semantics (Runtime vs Validation)

### Signal Lookback Semantik (primary_breakout_v1)
- **Zeitgestempelte Historie**: High/Low-Werte werden mit `ts_ms` gepflegt.
- **Zeitfenster-Lookback**: Entry-/Exit-Lookback werden als Zeitfenster (Minuten) evaluiert, nicht als Event-Count.
- **Warmup-Validierung**: Ein Signal wird nur generiert, wenn die Historie die volle Fenster-Spanne im aktuellen Fenster abdeckt (Warmup-Check).
- **Entscheidungs-Reihenfolge**: Die Entscheidung (Signal-Evaluierung) erfolgt **vor** dem Append des aktuellen Ticks/Candles in die Historie.

### Validation Gate Trace
- **Opt-in Diagnose**: Der `primary_breakout_v1` Gate-Trace ist eine opt-in Diagnosefläche für Backtests und Replays.
- **Kein Standard-Output**: Ohne explizites `--gate-trace-path` erfolgt keine Trace-Emission.
- **Audit-Zweck**: Dient der Identifizierung von Replay-/Paper-Drift durch detaillierte Protokollierung der Schwellenwert-Entscheidungen pro Schritt.

---

## 7. Invariants (nicht verhandelbar)

1. **Paper Trading Default**: Live Trading erfordert explizites Delivery Gate
2. **Event Sourcing**: Alle State-Aenderungen ueber Events (Replay-faehig)
3. **Circuit Breaker**: Risk Service gated alle Order Execution
4. **Determinismus**: Reproduzierbare Ergebnisse via Event Replay (LR-021: deterministic shadow replay via `core/replay/` stack)
5. **TLS Optional**: Aktivierbar via `-TLS` Flag (Redis + PostgreSQL)
6. **Localhost Binding**: Alle Ports auf 127.0.0.1 (keine externe Exposition)
7. **Secrets/Logging Hygiene**: Secret-Loader und SMTP-Alerter protokollieren keine secret-abgeleiteten Identifikatoren oder Empfaengeradressen im Klartext; Service-API-Fehlerantworten bleiben auf sichere Fehlercodes ohne Exception-/Stacktrace-Details begrenzt.
8. **Canonical Determinism**: Alle kanonischen Report-Felder sind frei von Wall-Clock-Zeit; deterministische JSON-Serialisierung via `core/replay/canonical_json.py` (LR-021)

---

## 6. Known Drifts (zu beheben)

Keine offenen Drifts.

Historisch behoben:
- prod.yml/tls.yml referenzierten `cdb_core` statt `cdb_signal` → behoben
- CLAUDE.md hatte Signal als Port 8001 → korrigiert auf 8005
- Market-Zeile Section 2: Retry/Reconnect + fail-closed /health Semantik ergänzt (issue #1646, 2026-04-16)

---

## 7. Compose Layer Referenz (kanonisch)

```
compose.blue.yml   -> BLUE: Data + Control + Core Trading  [kanonisch]
compose.red.yml    -> RED: Signal + Monitoring             [kanonisch]
logging.yml        -> Logging Overlay (Loki + Promtail + Alertmanager) [separates Overlay, nicht Standard-Start]
```

Legacy-Layer (base.yml, dev.yml, tls.yml, etc.) existieren noch, sind nicht mehr kanonisch.

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Build Sprint | Claude (Orchestrator) |
| 2026-03-29 | market_data Subscriber-Liste: cdb_market, cdb_candles, cdb_paper_runner ergaenzt (#1323) | Claude |
| 2026-03-29 | BLUE/RED reconciliation: alle Services nach Compose-Realitaet, Known Drifts bereinigt, Compose-Referenzen aktualisiert (#1302) | Claude |
| 2026-04-01 | Logging Overlay: Aktivierungsspalte auf compose-Datei-Referenz umgestellt (war: -Logging Flag); Compose-Referenzblock präzisiert (#1409) | Claude |
| 2026-04-11 | Signal-Port-Semantik präzisiert: Config-Default `SIGNAL_PORT=8001`, kanonischer Runtime-Port `8005` via `compose.red.yml` | Codex |
| 2026-04-18 | Security-Hygiene nach PR #1752 ergänzt: Secret-/SMTP-Logging ohne secret-abgeleitete Klartext-Details dokumentiert | Codex |
| 2026-04-18 | PR #1755 Nachzug: fail-closed Fehlerantworten ohne Stacktrace-/Exception-Text für Risk/Execution/Kill-Switch dokumentiert | Codex |
| 2026-04-20 | PR #1808 Nachzug: LR-021 deterministic replay infrastructure (core/replay + services/validation reporter/CLI) als Core Libraries dokumentiert (Issue #1809) | Codex |
| 2026-04-22 | PR #1856 Nachzug: ARVP §4.2 DatasetSpec + DatasetProvider (FileBackedDatasetProvider + DBBackedDatasetProvider) ergänzt (Issue #1857) | Codex |
| 2026-04-22 | PR #1859 Nachzug: `core/replay/scheduler.py` und minimaler Replay-CLI-Scheduler-Pfad (`speedup_profile`, `dataset_summary["scheduler"]`) ergänzt (Issue #1860) | Codex |
| 2026-04-23 | PR #1891 Nachzug: ARVP Operator-Facing Dataset Layer finalisiert (file\|db modes, db_dataset_window format, source-aware paths, legacy naming entfernt). CLI-Naming: run_accelerated_shadow_replay → run_arvp_replay (Issue #1892) | Codex |
| 2026-04-24 | PRs #1914/#1916/#1918/#1920 Nachzug: ARVP validation comparisons & scorecards. shadow_compare, replay_vs_paper_compare, simulator_calibration_report, arvp_regime_scorecards, paper_reference_window_export + CLI-Runner dokumentiert. Offline-Validation, keine Runtime-Komponenten. (Issues #1915/#1917/#1919/#1921) | Codex |
| 2026-05-13 | PR #2453/#2455 Nachzug: WS-Metrics-Delta-Logik + lazy `mexc_pb`-Client-Import sowie Postgres-Exporter-DSN/Secret-Wiring in RED-Compose dokumentiert (Issues #2454/#2456) | Codex |
| 2026-05-29 | PR #2670/#2671 Nachzug: `verify_stack.ps1` Default ohne Logging-Overlay; `-IncludeLogging:$true` fuer Loki/Promtail; Logging-Aktivierungspfad auf `infrastructure/compose/` praezisiert; Windows-`make docker-health` ergaenzt (Issue #2671) | Codex |
| 2026-06-05 | PRs #2999/#3001/#3003 Nachzug: Service-Map Code/README-Spalten; Paper Runner Code-Pfad `tools/paper_trading/`; Cross-Links zu `core/`, `services/`, `infrastructure/database/` READMEs (Issues #3000/#3004) | Cursor |
| 2026-06-05 | PRs #2989/#2992/#3006 Nachzug: `paper_runtime_stimulus_runner.py` als runtime-adjacent ARVP operator CLI dokumentiert; `stimulus_fixture`-Events mit `stimulus_run_id` erzeugen deterministische `signal_id`s fuer exportierbare paper chains. Kein Live-Go; keine DB-Schreibfläche (Issues #2990/#2993/#3008) | Codex |
| 2026-06-06 | PRs #3016/#3019/#3022 Nachzug: `paper_runtime_stimulus_runner.py` Determinismus-Härtung (`stimulus_run_id` -> `signal_id`) und Wall-Clock-Override für Stimulus-Freshness (RC_004 Safety) in `cdb_market` und `cdb_candles` dokumentiert (Issues #3017/#3020/#3023) | Codex |
| 2026-06-08 | PR #3081 Nachzug: `historical_bridge.py` + `evaluate_price_policies.py` als Replay-Infrastruktur-Komponenten dokumentiert; `price_policy`-Support vermerkt (Issue #3082) | Codex |
### PostgreSQL Schema Artefacts (PR #2793)

| Artifact | Migration | Status | Bedeutung |
|---|---|---|---|
| `risk_events` idempotency | `infrastructure/database/migrations/005_risk_events_idempotent.sql` | **AKTIV** | Fuegt `decision_pk` und `input_snapshot_hash` hinzu; der Unique-Key auf `decision_pk` macht Risk-Persistenz replay-sicher. |
| `correlation_ledger` | `infrastructure/database/migrations/006_correlation_phase8c.sql` | **AKTIV** | Append-only Audit-Trail fuer `SIGNAL`/`DECISION`/`ORDER`/`FILL`-Ketten; Grundlage fuer Export- und Replay-Referenzfenster. |
| `blocked_decisions` | `infrastructure/database/migrations/006_correlation_phase8c.sql` | **AKTIV** | Append-only Audit-Trail fuer BLOCK-Entscheidungen; nutzt denselben `decision_pk`-Mechanismus wie `risk_events`. |
