# Requirements Inventory Report
**Claire de Binare (CDB) Trading System**

**Generated**: 2026-02-09
**Repositories Scanned**:
- Working Repo: `./` (Claire_de_Binare repo root)
- Docs Hub: `../Claire_de_Binare_Docs` (documentation repo)

**Purpose**: Comprehensive inventory of all requirements, contracts, gates, policies, and service specifications that define deterministic logic in the CDB system.

---

## Table of Contents
1. [System-Level Governance](#1-system-level-governance)
2. [Service-Level Contracts](#2-service-level-contracts)
3. [Policy-as-Code Enforcement](#3-policy-as-code-enforcement)
4. [Gap Analysis](#4-gap-analysis)
5. [Top 10 Canonical Files](#5-top-10-canonical-files)

---

## 1. System-Level Governance

### 1.1 Live-Readiness Task Framework

**LR-TASKS.yaml** (`docs/live-readiness/LR-TASKS.yaml`)
- Single source of truth for which LR tasks exist (immutable task_id, append-only structure)
- Tasks Defined: LR-001 through LR-007
- Each task has corresponding STATE.yaml and EVIDENCE.md files

**Task Status Overview**:

| Task ID | Title | Priority | Status |
|---------|-------|----------|--------|
| LR-001 | P0 Governance CI/CD Shield | P0 | DONE |
| LR-002 | P0 Contract Tests | P0 | DONE |
| LR-003 | P0 Contract Drift Guard | P0 | DONE |
| LR-004 | P0 Deterministic Completion Mechanism | P0 | DONE |
| LR-005 | Deterministic Completion Reporting & State Visibility | P1 | DONE |
| LR-006 | P0 Deterministic Decision Traceability Contract | P0 | DONE |
| LR-007 | Shadow Mode Validation Gate | P0 | BLOCKED |

### 1.2 Governance Foundation

**META-001: Governance Foundation Consolidation** (`docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md`)
- Consolidated decision-only governance for Live Readiness tasks LR-001 through LR-006A
- Key Contracts: CI-enforced protection, contract drift guards, deterministic state files (no GitHub API dependency), decision trace contracts
- Determinism: Audit-capable completion tracking via YAML state files with Git-native audit trail

**Key Invariants**:
- No GitHub API Dependency: LR-004 state files are Git-native
- Deterministic State: All LR task states validated via `lr004_completion_guard.py` with 15 validation rules
- Fail-Closed Protection: Invalid state files block merge automatically
- Immutable Audit Trail: All governance changes tracked in Git history
- Terminal States Only: DONE or BLOCKED states (no intermediate states)

### 1.3 CI/CD Shield

**LR-001 Evidence** (`docs/live-readiness/LR-001-EVIDENCE.md`)
- Governs: 8 required status checks on main branch with admin bypass prevention
- Required Checks:
  - `ci (Unit/Integration + Lint)`
  - `validate-branch-name`
  - `gitleaks` (secret scanning)
  - `trivy` (security scanning)
  - `Check Core Duplicates`
  - `Check Delivery Gate`
  - `guard` (governance guard)
  - `E2E Happy Path`
- Determinism: GitHub branch protection enforces `strict: true` (branch must be up-to-date before merge)

### 1.4 Contract Drift Protection

**LR-003 Contract Drift Guard** (`scripts/lr003_contract_drift_guard.py`)
- Governs: SHA256 fingerprint-based protection for critical contract files
- Protected Files:
  - `docs/contracts/market_data.schema.json`
  - `docs/contracts/signal.schema.json`
  - `services/risk/reason_codes.py`
  - `tests/contract/test_decision_contract.py`
- Determinism: Combined SHA256 hash (`d728e2e133d6d2dbd6139fe1b355ef1da30fc2eb973bdcbfb7fb5815cd90e779`) stored in `docs/live-readiness/LR-003-FINGERPRINT.json`
- Enforcement: CI blocks merge if fingerprint mismatch detected

**Risk Events Schema Drift Guard** (`scripts/governance/check_risk_events_schema_contract.py`)
- Validates `services/risk/service.py` INSERT statement columns match `docs/governance/risk_events.schema.yaml`
- Detects: columns in code but not in spec, or vice versa
- Enforcement: CI workflow `core-guard.yml` (exit code 1 blocks merge)

### 1.5 Completion & State Management

**LR-004 Specification** (`docs/live-readiness/LR-004-SPEC.md`)
- Governs: Fail-closed task state validation with binary terminal states (DONE/BLOCKED)
- Key Gates: Manifest validation (V000-V002), state file validation (V003-V015), reason code taxonomy (RC_B001-RC_B402)
- Validator: `lr004_completion_guard.py` implements 15 validation rules with fail-closed enforcement

**State File Requirements**:
- DONE state: `completion_timestamp` (ISO 8601 UTC), `completion_author`, `evidence_file`, `evidence_commit`
- BLOCKED state: `blocked_reason_code`, `blocked_reason_text`, `blocked_since`
- Invariants: No intermediate states, all required fields mandatory atomically, immutable task manifest

**Valid Reason Codes**:
- RC_B001: Upstream dependency
- RC_B002: External system
- RC_B003: Third-party API quota
- RC_B100-RC_B102: Resource constraints (budget, infrastructure, personnel)
- RC_B200-RC_B202: Technical blockers (critical bug, technology limitation, security/compliance)
- RC_B300-RC_B302: Organizational blockers (stakeholder decision, policy change, cross-team)
- RC_B400-RC_B402: Requirements issues (clarification needed, scope change, unachievable criteria)

### 1.6 Decision Traceability

**LR-006 Decision Trace Contract** (`docs/live-readiness/LR-006-EVIDENCE.md`)
- Governs: Deterministic traceability for order decisions, lifecycle decisions, parameter selections
- Structure: trace_id, decision_id, decision_type, decision_outcome, input_set, version_set, constraint_set, evidence artefacts
- Determinism: Replay-verifiable via Git SHA + code line ranges, snapshots, policy references
- Key Invariant: No secrets in traces (config hashes instead of inline values)

### 1.7 Delivery & Human Gates

**Delivery Gate** (`governance/DELIVERY_APPROVED.yaml`)
- Governs: Human-controlled delivery approval (Constitution §4.2: only humans may approve)
- Current State: `approved: true` (reason: "Governance Audit Phase 1 complete")
- Exception Labels: `docs-only`, `ci-only`, `emergency` (bypass gate if present)
- Workflow: `.github/workflows/delivery-gate.yml` enforces via CI check

**Live Trading Gate** (`services/risk/live_trading_gate.py`)
- Governs: Authorization levels for live trading (DENIED, PAPER_ONLY, LIMITED, FULL)
- Key Invariant: Requires successful 72-hour test completion before FULL authorization
- Implementation: Validates real test results (no fake green), caches authorization per system_id

**Gate Evaluator** (`services/validation/gate_evaluator.py`)
- Governs: Pass/fail evaluation for 72h validation summaries via GateThresholds
- Configurable Thresholds: min_orders (10), min_fill_rate (0.45), min_qty_sum (1.0)
- Criteria: Evaluates orders_total, filled_total, qty_sum against environment-based config

### 1.8 Weekly Governance Process

**Weekly Review Process** (`governance/WEEKLY_REVIEW_PROCESS.md`)
- Governs: Structured weekly audits covering security findings, PR health, milestone progress, policy compliance, stale issues
- Key Gates:
  - Zero HIGH/CRITICAL vulnerabilities tolerated >7 days
  - PRs >7 days without review flagged
  - Draft PRs >14 days flagged
- Owner: Jannek Buengener (Maintainer)
- Schedule: Every Monday 10:00 CET

### 1.9 Secrets Management

**Secrets Policy** (`governance/SECRETS_POLICY.md`)
- Secrets Locations: Outside repository (`C:\Users\<username>\Documents\.secrets\.cdb\`)
- Tracked Secrets: None (no secrets in Git history)
- CI/CD Secrets: Stored in GitHub Actions Secrets (GEMINI_API_KEY, CLAUDE_API_KEY)
- Invariant: Rotate all secrets after clone (previous versions had secrets in history)

### 1.10 Branch Protection Policy

**Branch Protection** (`docs/operations/branch_protection_policy.md`)
- Enforced State:
  - `allow_force_pushes: false`
  - `allow_deletions: false`
  - `required_approving_review_count >= 1`
  - `strict: true` (branch must be up-to-date)
- Canonical Config: `temp_branch_protection.json` (to be moved to Docs Hub governance/)

---

## 2. Service-Level Contracts

### 2.1 Stream Topology Overview

```
┌─────────────────────────────────────────────────────────┐
│            MARKET DATA FEED (WebSocket)                 │
│                  bot_ws Service                         │
└──────────────────────────────┬──────────────────────────┘
                               │
                        market_data (Pub/Sub)
                               │
                   ┌───────────┴───────────┐
                   │                       │
        ┌──────────▼──────────┐  ┌──────────▼──────────┐
        │  Signal Service     │  │  Candles Service    │
        │  (Momentum)         │  │  (OHLCV Agg)        │
        │  Port 8001          │  │  Port 8007          │
        └──────────┬──────────┘  └──────────┬──────────┘
                   │                        │
          stream.signals          stream.candles_1m
                   │                        │
                   └────────────┬───────────┘
                                │
                   ┌────────────▼──────────┐
                   │  Regime Service       │
                   │  (ADX/ATR)            │
                   │  Port 8008            │
                   └──────────┬─────────────┘
                              │
                    stream.regime_signals
                              │
                   ┌──────────┴───────────┐
                   │                      │
        ┌──────────▼──────────┐ ┌────────▼────────┐
        │  Risk Manager       │ │ Allocation Svc  │
        │  (5-Layer)          │ │ (Performance)   │
        │  Port 8002          │ │ Port 8005       │
        └──────────┬──────────┘ └────────┬────────┘
                   │                     │
            stream.orders   stream.allocation_decisions
                   │                     │
                   └─────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │ Execution Service  │
                   │ (MEXC/Mock)        │
                   │ Port 8003          │
                   └──────────┬─────────┘
                              │
                        stream.fills
                              │
                   ┌──────────┴──────────┐
                   │                     │
        ┌──────────▼──────────┐ ┌───────▼─────────┐
        │  Risk (State)       │ │  Allocation     │
        │  Update             │ │  (Trade Record) │
        └─────────────────────┘ └─────────────────┘
```

### 2.2 Signal Service (Port 8001)

**Status**: Production-ready

**Input**: `market_data` (Redis Pub/Sub channel)

**Output**: `stream.signals` (Redis Stream, configurable via `SIGNAL_OUTPUT_STREAM`)

**Data Contract - Signal Model** (`services/signal/models.py`):
- `schema_version`: "v1.0" (required)
- `signal_id`: string (optional)
- `strategy_id`: string (optional)
- `bot_id`: string (optional)
- `symbol`: string (required)
- `direction`: string (legacy, being phased out)
- `side`: "BUY" | "SELL" (required)
- `strength`: float 0.0-1.0 (required)
- `confidence`: float 0.0-1.0 (required)
- `timestamp`: float | int (required)
- `reason`: string (optional)
- `price`: float (optional)
- `pct_change`: float (optional, momentum indicator)
- `pct_change_15m`: float (optional)
- `volume_15m`: float (optional)
- `ts_ms`: int (optional, milliseconds)
- `type`: "signal" (literal)

**Deterministic Behavior**:
- Threshold: `SIGNAL_THRESHOLD_PCT` (default: 3.0%)
- Lookback: `SIGNAL_LOOKBACK_MIN` (default: 15 minutes)
- Min Volume: `SIGNAL_MIN_VOLUME` (default: 100000)
- Top-N selection based on momentum score calculation
- No probabilistic scoring - confidence is informational only

**Key Files**:
- `services/signal/config.py` - Configuration & ENV validation
- `services/signal/models.py` - Signal & MarketData dataclasses
- `services/signal/service.py` - Main service logic
- `services/signal/README.md` - Service specification

### 2.3 Candles Service (Port 8007)

**Status**: Production-ready

**Input**: `market_data` (Redis Pub/Sub channel)

**Output**: `stream.candles_1m` (Redis Stream)

**Data Contract - Candle Model** (`services/candles/models.py`):
- `symbol`: string (required)
- `start_ts`: int (window start, seconds, aligned to minute boundary)
- `interval_seconds`: int (default: 60)
- `open`: float (required)
- `high`: float (required)
- `low`: float (required)
- `close`: float (required)
- `volume`: float (required)
- `trade_count`: int (required)

**Stream Payload Format**:
```json
{
  "ts": "seconds",
  "symbol": "BTCUSDT",
  "timeframe": "60s",
  "open": "50000.12345678",
  "high": "50100.00000000",
  "low": "49900.00000000",
  "close": "50050.00000000",
  "volume": "12.34567890",
  "trades": "125"
}
```

**Deterministic Behavior**:
- Window alignment: Start timestamp aligned to minute boundaries
- Aggregation: OHLCV calculation from trade stream
- Precision: 8 decimal places preserved as strings

**Required ENV**:
- `CANDLE_INTERVAL_SECONDS` (required, e.g., 60 for 1-minute)

**Key Files**:
- `services/candles/config.py`
- `services/candles/models.py`
- `services/candles/service.py`

### 2.4 Regime Service (Port 8008)

**Status**: Production-ready (deterministic)

**Input**: `stream.candles_1m` (from Candles service)

**Output**: `stream.regime_signals` (Redis Stream)

**Data Contract - Regime Signal**:
```json
{
  "ts": 1234567890,
  "symbol": "BTCUSDT",
  "timeframe": "1m",
  "regime": "TREND" | "RANGE" | "HIGH_VOL_CHAOTIC" | "UNKNOWN",
  "adx": 35.5,
  "atr": 125.3,
  "source_version": "1",
  "schema_version": "1"
}
```

**Deterministic Rules**:
- ADX > `REGIME_ADX_TREND_THRESHOLD` → TREND regime
- ADX ≤ `REGIME_ADX_RANGE_THRESHOLD` → RANGE regime
- ATR ≥ `REGIME_ATR_HIGH_VOL_THRESHOLD` → HIGH_VOL_CHAOTIC regime
- Confirmation bars: `REGIME_CONFIRMATION_BARS` (must see same regime N consecutive bars)
- Fallback: UNKNOWN if missing OHLCV data

**Required ENV Variables**:
- `REGIME_ADX_PERIOD` (required, e.g., 14)
- `REGIME_ATR_PERIOD` (required, e.g., 14)
- `REGIME_ADX_TREND_THRESHOLD` (required, e.g., 25)
- `REGIME_ADX_RANGE_THRESHOLD` (required, e.g., 20)
- `REGIME_ATR_HIGH_VOL_THRESHOLD` (required, e.g., 150)
- `REGIME_CONFIRMATION_BARS` (required, e.g., 3)

**Key Files**:
- `services/regime/config.py`
- `services/regime/models.py` (contains compute_adx, compute_atr)
- `services/regime/service.py`
- `services/regime/README.md`

### 2.5 Allocation Service (Port 8005)

**Status**: Production-ready (deterministic)

**Input Streams**:
- `stream.regime_signals` (from Regime Service)
- `stream.fills` (from Execution Service - trade fills)
- `stream.bot_shutdown` (system shutdown)

**Output**: `stream.allocation_decisions` (Redis Stream)

**Data Contract - Allocation Decision**:
```json
{
  "ts": 1234567890,
  "strategy_id": "momentum_v1",
  "allocation_pct": 0.35,
  "regime": "TREND",
  "decision": "ALLOCATE" | "REDUCE" | "MAINTAIN",
  "reason": "Strong performance in TREND regime",
  "source_version": "1",
  "schema_version": "1"
}
```

**Deterministic Rules**:
- Lookback: 30 trades AND 7 days minimum
- EMA Alpha: 0.3 (exponential smoothing)
- Cooldown: 72 hours after regime change
- Regime Stability Required: `ALLOCATION_REGIME_MIN_STABLE_SECONDS` (typically 300-600s)
- Performance-based allocation scaling (median return calculation over lookback window)

**Required ENV**:
- `ALLOCATION_RULES_JSON` (JSON config dict)
- `ALLOCATION_REGIME_MIN_STABLE_SECONDS` (required)

**Key Files**:
- `services/allocation/config.py`
- `services/allocation/service.py`
- `services/allocation/README.md`

### 2.6 Risk Service (Port 8002)

**Status**: Production-ready (5-layer deterministic validation)

**Input Streams/Topics**:
- `signals` (from Signal Service)
- `stream.regime_signals` (from Regime Service)
- `stream.allocation_decisions` (from Allocation Service)
- `stream.bot_shutdown` (system shutdown signal)
- `order_results` (from Execution Service - for state updates)

**Output Streams/Topics**:
- `stream.orders` (Redis Stream - approved orders)
- `alerts` (Redis Topic/Stream)

**Data Contract - Order Model** (`services/risk/models.py`):
- `symbol`: string (required)
- `side`: "BUY" | "SELL" (required)
- `quantity`: float (required)
- `stop_loss_pct`: float (required)
- `signal_id`: int (required)
- `reason`: string (required)
- `timestamp`: int (required)
- `strategy_id`: string (required)
- `bot_id`: string (optional)
- `client_id`: string (optional)
- `price`: float (optional)
- `type`: "order" (literal)

**Data Contract - Alert Model**:
- `level`: "INFO" | "WARNING" | "CRITICAL" (required)
- `code`: string (RC_xxx reason codes)
- `message`: string (required)
- `context`: dict (required)
- `timestamp`: int (required)
- `type`: "alert" (literal)

**Deterministic Decision Logic (5-Layer Hierarchy)**:

```
DEFAULT: BLOCK (Fail-safe principle)
ALLOW: ONLY if Layer 1 ∧ Layer 2 ∧ Layer 3 ∧ Layer 4 ∧ Layer 5

Layer 1: Circuit Breaker
  ├─ daily_loss < MAX_DAILY_DRAWDOWN_PCT (default 5%)
  ├─ Action if violated: BLOCK all orders, Alert CRITICAL
  └─ Reason Code: RC_002

Layer 2: Position Size
  ├─ order.quantity ≤ MAX_POSITION_PCT × capital (default 10%)
  ├─ Action if violated: TRIM or REJECT
  └─ Reason Code: RC_010

Layer 3: Total Exposure
  ├─ sum(all_positions) ≤ MAX_TOTAL_EXPOSURE_PCT × capital (default 50%)
  ├─ Action if violated: BLOCK new orders
  └─ Reason Code: RC_020

Layer 4: Anomaly Detection
  ├─ Slippage < 1%
  ├─ Spread < 5× normal
  ├─ Data staleness < 30 seconds
  ├─ Action if violated: PAUSE trading
  └─ Reason Codes: RC_001 (stale), RC_003 (slippage), RC_004 (spread)

Layer 5: Order Validation
  ├─ Symbol valid (on whitelist)
  ├─ Side valid (BUY | SELL)
  ├─ Price positive & reasonable
  ├─ Quantity positive
  ├─ Stop-Loss ≥ STOP_LOSS_PCT
  └─ Reason Codes: RC_021, RC_022
```

**Risk Limits Configuration**:
- `MAX_POSITION_PCT = 0.10` (10% per trade)
- `MAX_TOTAL_EXPOSURE_PCT = 0.50` (50% total)
- `MAX_DAILY_DRAWDOWN_PCT = 0.05` (5% daily loss limit)
- `STOP_LOSS_PCT = 0.02` (2% stop-loss per position)
- `EARLY_LIVE_MAX_ALLOC = 0.02` (2% early live mode limit)

**Key Files**:
- `services/risk/config.py`
- `services/risk/models.py` (Order, Alert, RiskState)
- `services/risk/service.py`
- `services/risk/README.md`
- External Docs Hub (not in this repo): `knowledge/deep-issues-lab/cdb_risk.md` (deep-dive)

### 2.7 Execution Service (Port 8003)

**Status**: Production-ready (Paper Trading Mode)

**Input Streams/Topics**:
- `orders` (from Risk Manager - Redis Topic or Stream)
- `stream.bot_shutdown` (system shutdown)

**Output Streams/Topics**:
- `stream.fills` (Redis Stream - order results)
- `order_results` (Redis Topic - backward compat)
- `alerts` (alerts on execution errors)

**Data Contract - Order Input** (`services/execution/models.py`):
- `symbol`: string (required)
- `side`: "BUY" | "SELL" (required)
- `quantity`: float (required)
- `stop_loss_pct`: float (optional)
- `strategy_id`: string (optional)
- `bot_id`: string (optional)
- `client_id`: string (optional)
- `timestamp`: int | float | string (optional)
- `type`: "order" (literal)

**Data Contract - Execution Result**:
- `order_id`: string (required)
- `symbol`: string (required)
- `side`: "BUY" | "SELL" (required)
- `quantity`: float (required)
- `filled_quantity`: float (required)
- `status`: "FILLED" | "REJECTED" | "ERROR" (required)
- `strategy_id`: string (optional)
- `bot_id`: string (optional)
- `client_id`: string (optional)
- `price`: float (optional)
- `error_message`: string (optional)
- `timestamp`: string (ISO format, optional)
- `type`: "order_result" (literal)

**Deterministic Behavior (Paper Trading Mode)**:
- Success Rate: 95% simulated (configurable)
- Order Types: MARKET (primary), LIMIT (future), STOP_LOSS_LIMIT (future)
- Execution: Immediate fill with realistic slippage simulation
- Commission: 0.1% per fill
- Timestamp: UTC ISO format or Unix seconds

**Key Configuration**:
- `MOCK_TRADING = True` (Paper trading mode)
- `DRY_RUN = True` (Safety: log without executing)
- `STREAM_ORDER_RESULTS = "stream.fills"`
- `STREAM_BOT_SHUTDOWN = "stream.bot_shutdown"`

**Key Files**:
- `services/execution/config.py`
- `services/execution/models.py` (Order, ExecutionResult, Trade)
- `services/execution/service.py`
- `services/execution/EXECUTION_SERVICE_STATUS.md`
- External Docs Hub (not in this repo): `knowledge/deep-issues-lab/cdb_execution.md` (MEXC API contracts, error handling)

### 2.8 Redis Stream Specifications

**Stream Communication Pattern**: All inter-service communication uses Redis Streams (XADD/XREAD)

| Stream Name | Publisher | Subscriber(s) | Maxlen | Content Type |
|-------------|-----------|---------------|--------|--------------|
| `stream.signals` | Signal Service | Risk Manager, Dashboard | 10000 | Signal events |
| `stream.regime_signals` | Regime Service | Allocation, Risk Manager | 10000 | Regime events |
| `stream.candles_1m` | Candles Service | Regime Service | 10000 | OHLCV candles |
| `stream.allocation_decisions` | Allocation Service | Risk Manager | 10000 | Allocation events |
| `stream.orders` | Risk Manager | Execution, Persistor | 10000 | Order events |
| `stream.fills` | Execution Service | Risk, Allocation, Persistor | 10000 | Fill/OrderResult events |
| `stream.bot_shutdown` | System | All Services | 1000 | Shutdown signals |

**Redis Operations**:
- `XADD`: Add event to stream (atomic, with maxlen for memory management)
- `XREAD`: Blocking stream reads with consumer group support
- All events: JSON-serialized strings with `schema_version` field

### 2.9 Market Data Interface

**Topic**: `market_data` (Redis Pub/Sub)

**Contract Model** (`services/signal/models.py`):
- `symbol`: string (required)
- `price`: float (required)
- `timestamp`: int (required)
- `schema_version`: string (optional)
- `source`: string (optional)
- `trade_qty`: float (optional, migrated from `qty`)
- `pct_change`: float (optional)
- `open`: float (optional)
- `high`: float (optional)
- `low`: float (optional)
- `close`: float (optional)
- `volume`: float (default: 0.0)
- `interval`: string (default: "15m")
- `venue`: string (optional)
- `side`: string (optional)
- `trade_id`: string (optional)
- `type`: "market_data" (literal)

**Required Fields**: symbol, price, timestamp
**Legacy Fallbacks**: `ts_ms` → `timestamp`, `qty` → `trade_qty`

---

## 3. Policy-as-Code Enforcement

### 3.1 Message Contract Schemas

**Market Data Schema** (`docs/contracts/market_data.schema.json`)
- JSON Schema v7
- Required fields: `schema_version` (const "v1.0"), `source`, `symbol`, `ts_ms`, `price` (string), `trade_qty` (string), `side`
- Rejects legacy `qty` field (migration to `trade_qty`)
- `additionalProperties: false` (strict schema enforcement)
- Price/quantity as strings (preserves precision, prevents float errors)

**Signal Schema** (`docs/contracts/signal.schema.json`)
- JSON Schema v7
- Required fields: `schema_version` (const "v1.0"), `signal_id`, `strategy_id`, `symbol`, `side` (enum: BUY/SELL), `timestamp`
- Rejects legacy `direction` field (migration to `side`)
- `additionalProperties: false` (strict schema enforcement)
- `strength`/`confidence` must be 0.0-1.0 range
- `timestamp` must be integer (seconds, not float)

**Enforcement**: CI workflow `contracts.yml` runs pytest validation tests and JSON schema syntax checks

### 3.2 Risk Decision Contract Tests

**Test Suite** (`tests/contract/test_decision_contract.py`)

**16 Deterministic Contract Tests**:
1. `test_decision_allow` - Baseline allow decision
2. `test_decision_rc_001_regime_block` - RC_001: Regime blocks order
3. `test_decision_rc_002_panic_return_1m` - RC_002: Panic detection (1m return < -2%)
4. `test_decision_rc_002_panic_return_5m` - RC_002: Panic detection (5m return < -2%)
5. `test_decision_rc_003_stale` - RC_003: Stale data (>5s old)
6. `test_decision_rc_004_data_silence` - RC_004: Data silence (>30s gap)
7. `test_decision_rc_010_signal_thresholds` - RC_010: Signal below 3.0% pct_change
8. `test_decision_rc_020_daily_drawdown` - RC_020: Daily drawdown >2%
9. `test_decision_rc_021_exposure` - RC_021: Exposure >30%
10. `test_decision_rc_022_slippage` - RC_022: Slippage >1.0%
11. `test_decision_determinism` - Same inputs always produce same outputs
12. `test_decision_first_fail_panic_wins` - Priority: panic > stale > regime > signal
13. `test_decision_first_fail_stale_wins_over_regime` - Order of checks matters
14. `test_decision_first_fail_regime_wins_over_signal` - Hierarchical blocking
15. `test_decision_first_fail_drawdown_wins_over_exposure` - Risk checks prioritized
16. Additional edge cases for deterministic ordering

**Invariants Enforced**:
- Deterministic decision logic with explicit reason codes (RC_*)
- Ordered evaluation (panic → stale → regime → signal thresholds → exposure limits)
- Fail-closed design (default BLOCK unless all checks pass)

**Enforcement**: Run in main CI workflow `.github/workflows/ci.yaml` (`contract-tests` job running `pytest -m contract`); `contracts.yml` separately runs `tests/unit/contracts/test_contracts.py` and JSON schema JSON-validity checks

### 3.3 Schema Drift Guards

**LR-003 Contract Fingerprint Guard** (`scripts/lr003_contract_drift_guard.py`)
- Protected Files (hardcoded):
  - `docs/contracts/market_data.schema.json`
  - `docs/contracts/signal.schema.json`
  - `services/risk/reason_codes.py` (8 RC constants)
  - `tests/contract/test_decision_contract.py` (16 tests)
- Enforcement: SHA256 hashing with combined fingerprint
- Per-file SHA256 + combined SHA256
- Fingerprint stored in: `docs/live-readiness/LR-003-FINGERPRINT.json`
- Modes:
  - `--generate`: Creates fingerprint
  - `--check`: Validates contracts against fingerprint
- Gating: Exit code 0 (no drift) / Exit code 1 (drift detected, blocks CI)

**Risk Events Schema Contract** (`scripts/governance/check_risk_events_schema_contract.py`)
- Validates `services/risk/service.py` INSERT statement columns match `docs/governance/risk_events.schema.yaml`
- Detects drift: columns in code but not in spec, or vice versa
- Order mismatch: warning (not fail, but alerts)
- Gating: CI workflow `core-guard.yml` (exit code 1 blocks merge)

### 3.4 Core Integrity Guards

**Core Duplicate & Secrets Guard** (`scripts/check_core_duplicates.py`)
- Rule 1: No `services/*/core/**` directories allowed (prevents duplication)
- Rule 2: No additional `secrets.py` files except `core/domain/secrets.py`
- Gating: CI workflow `core-guard.yml` (exit code 1 blocks merge)

**Governance Drift Guard** (`.github/workflows/docs-hub-guard.yml`)
- Forbids local `.claude/agents/` directory
- Prevents split-brain with canonical definitions in `Claire_de_Binare_Docs` repo
- Gating: CI workflow `docs-hub-guard.yml` blocks if directory exists (exit code 1)

### 3.5 LR-005 Schema Compliance Tests

**Test Suite** (`tests/integration/test_lr005_schema_compliance.py`)

**Schema** (`docs/live-readiness/LR-005-SCHEMA.json` - JSON Schema Draft 7)

**Invariants Enforced**:
- Required fields: `spec_version`, `snapshot_metadata`, `summary`, `tasks`, `blocked_details`
- `spec_version`: pattern `^[0-9]+\.[0-9]+$`
- `task_id`: pattern `^LR-[0-9]{3}$` (e.g., LR-001)
- `git_commit`: pattern `^[a-f0-9]{7,40}$` (hex SHA)
- `completion_percentage`: 0-100 range
- `blocked_*` fields null for DONE tasks
- `completion_*` fields null for BLOCKED tasks
- `blocked_details` is subset of BLOCKED tasks

**9 Tests**:
1. `test_schema_itself_is_valid()` - Meta-schema validation
2. `test_example_done_validates_against_schema()` - Valid done snapshot
3. `test_example_blocked_validates_against_schema()` - Valid blocked snapshot
4. `test_schema_rejects_invalid_spec_version()`
5. `test_schema_rejects_missing_required_fields()`
6. `test_schema_rejects_invalid_task_id_format()`
7. `test_schema_rejects_invalid_git_commit_format()`
8. `test_schema_rejects_completion_percentage_out_of_range()`
9. Deterministic subset/consistency checks

**Gating**: Part of pytest suite, validation failure blocks merge

### 3.6 LR-004 Completion Guard

**Validator** (`scripts/lr004_completion_guard.py`)

**Enforcement Type**: YAML manifest validation with reason code taxonomy

**Valid Reason Codes (hardcoded)**: RC_B001-RC_B402 (documented in section 1.5)

**15 Validation Rules**:
- V000-V002: Manifest validation
- V003-V015: State file validation (YAML structure, required fields, field nullability, reason code taxonomy)

**Gating**:
- Exit code 0: All tasks valid
- Exit code 1: Validation failure (blocks merge)
- Exit code 2: Configuration error

### 3.7 Database Schema Constraints

**PostgreSQL Constraints** (`infrastructure/database/schema.sql`)

**signals table**:
- `CHECK: signal_type IN ('buy', 'sell')`
- `CHECK: confidence >= 0 AND confidence <= 1`
- `CHECK: LENGTH(symbol) >= 3`

**orders table**:
- `CHECK: side IN ('buy', 'sell', 'long', 'short')`
- `CHECK: order_type IN ('market', 'limit', 'stop', 'stop_limit')`
- `CHECK: status IN ('pending', 'submitted', 'filled', 'partial', 'cancelled', 'rejected')`
- `CHECK: size > 0`
- `CHECK: filled_size >= 0 AND filled_size <= size`

**trades table**:
- `CHECK: status IN ('filled', 'partial', 'cancelled')`
- `CHECK: size > 0`
- `CHECK: price > 0`

**positions table**:
- `CHECK: side IN ('long', 'short', 'none')`
- `CHECK: size >= 0`

**portfolio_snapshots table**:
- `CHECK: total_equity > 0`
- `CHECK: available_balance >= 0`
- `CHECK: total_exposure_pct >= 0 AND total_exposure_pct <= 1`

**Gating**: Database layer enforcement (constraints block invalid INSERT/UPDATE at runtime)

### 3.8 Docker Healthcheck Enforcement

**Configuration** (`infrastructure/compose/healthchecks-strict.yml`)

**Services with Healthchecks**:
- `cdb_db_writer`: Python healthcheck for Redis/Postgres connectivity
- `cdb_signal`: depends_on cdb_redis, cdb_postgres, cdb_ws (service_healthy)
- `cdb_risk`: depends_on cdb_signal, cdb_redis
- `cdb_execution`: depends_on cdb_risk, cdb_redis, cdb_postgres

**Invariants**:
- Service health timeouts: 30s interval, 10s timeout, 3 retries
- Start period: 30-60s (graceful startup)
- Ordered startup: execution cannot start until risk is healthy

**Gating**: Fail-closed - services wait for dependencies, cannot start unhealthy

### 3.9 CI/CD Workflow Enforcement

**contracts.yml** (`.github/workflows/contracts.yml`)
- Validates: Contract schemas (market_data, signal, decision) via pytest tests
- Enforces: Breaking changes blocked via LR-003 fingerprint comparison
- Trigger: Push/PR to main

**core-guard.yml** (`.github/workflows/core-guard.yml`)
- Validates: Schema drift + core duplicates
- Scripts: `check_risk_events_schema_contract.py`, `check_core_duplicates.py`
- Trigger: Push/PR to main

**governance-drift-guard.yml** (`.github/workflows/governance-drift-guard.yml`)
- Validates: No `.claude/agents/` directory exists
- Reason: Prevents split-brain with Docs Hub canonical definitions
- Trigger: Push/PR to main

**delivery-gate.yml** (`.github/workflows/delivery-gate.yml`)
- Validates: `governance/DELIVERY_APPROVED.yaml` approval status
- Bypass: Labels `docs-only`, `ci-only`, `emergency`
- Trigger: Push/PR to main

### 3.10 Contract Validation CLI Tool

**Tool** (`tools/validate_contract.py`)

**Features**:
- Runtime message validation against JSON schemas
- Type coercion (string → integer/number)
- Multiple payload sources: file, stdin, Redis streams
- Draft7Validator enforcement

**Usage**:
```bash
python tools/validate_contract.py market_data --file payload.json
python tools/validate_contract.py signal --stdin < signal.json
```

**Gating**: Validation errors block with detailed error reporting

### 3.11 Pytest Configuration & Markers

**Test Markers for Determinism**:
- `@pytest.mark.contract` - Deterministic contract tests (16 tests)
- `@pytest.mark.unit` - Unit tests (559 tests total)
- `@pytest.mark.integration` - Integration tests with state

**Configuration**: `pyproject.toml` with Ruff/Black linting rules

**Test Coverage**: 559 tests across unit/integration/contract markers

---

## 4. Gap Analysis

### 4.1 Blocked Tasks

**LR-007: Shadow Mode Validation Gate** (BLOCKED)
- Status: BLOCKED (reason: RC_B001 - Upstream dependency on paper trading validation)
- Impact: Cannot validate live trading readiness without successful shadow mode soak test
- Priority: P0 (critical path to live trading)
- Next Steps: Complete paper trading validation, execute 72-hour shadow mode soak test

### 4.2 Missing Governance Areas

**Paper Trading Validation** (Incomplete)
- Current State: Execution service in paper trading mode (95% simulated fill rate)
- Missing: 72-hour soak test validation, performance metrics baseline
- Impact: Cannot gate live trading authorization (FULL level blocked)
- Priority: P0

**ML Model Governance** (Deferred to M5-M9)
- Current State: No ML models in production
- Missing: Model versioning, drift detection, retraining policies, feature store contracts
- Impact: Cannot deploy ML-based signals (LR-008 not started)
- Priority: P1 (deferred to Q1/Q2 2026)

**Agent Autonomy Boundaries** (Not Defined)
- Current State: No write-gate policy for autonomous agent commits
- Missing: Clear boundaries for agent actions (read-only vs. write-allowed), approval gates
- Impact: Risk of unintended autonomous changes to critical files
- Priority: P2

**Observability SLO Enforcement** (No Runtime Gates)
- Current State: Prometheus/Grafana/Loki infrastructure exists, no SLO enforcement
- Missing: Alerting rules that block deployments on SLO violations, runbook automation
- Impact: Cannot enforce latency/availability/error rate contracts
- Priority: P2

**Multi-Task-Type Support** (LR-Tasks Only)
- Current State: Only LR-Tasks supported (LR-001 through LR-007)
- Missing: Incident tasks, Feature tasks, Epic tasks
- Impact: Limited task tracking for non-live-readiness work
- Priority: P3

**SLA Auto-Escalation** (No Blocked Task Aging Policy)
- Current State: Manual review of blocked tasks, no automatic escalation
- Missing: Auto-escalation for `blocked_since > N days`, notification automation
- Impact: Blocked tasks can stagnate without visibility
- Priority: P3

### 4.3 Weak Areas (Need Strengthening)

**Contract Drift Detection Coverage** (Partial)
- Strong: LR-003 protects 4 files (market_data.schema.json, signal.schema.json, reason_codes.py, test_decision_contract.py)
- Weak: Other contracts not fingerprinted (regime signal, allocation decision, candles)
- Recommendation: Expand LR-003 to cover all service interface contracts

**Decision Traceability Implementation** (Specification Complete, Implementation Partial)
- Strong: LR-006 specification defines trace structure, replay-verifiable format
- Weak: No automated trace generation for all decision types (only manual examples in evidence)
- Recommendation: Implement trace generation middleware for risk decisions, lifecycle decisions, parameter selections

**Service Interface Documentation** (Strong in Code, Weak in Central Docs)
- Strong: READMEs in each service directory document contracts
- Weak: No central service catalog or API documentation (e.g., OpenAPI specs)
- Recommendation: Generate central service catalog from code annotations

**Risk Reason Code Taxonomy** (8 codes defined, limited coverage)
- Strong: 8 risk reason codes (RC_001-RC_022) with deterministic tests
- Weak: Limited coverage for allocation decisions, regime transitions, execution errors
- Recommendation: Expand reason code taxonomy to cover all decision types

---

## 5. Top 10 Canonical Files

These files should be treated as "source of truth" for the CDB system:

### 1. `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md`
**Why**: Consolidated governance foundation for LR-001 through LR-006A, defines deterministic principles, fail-closed gates, audit trail contracts

### 2. `docs/contracts/market_data.schema.json`
**Why**: JSON Schema v7 contract for market data messages, protected by LR-003 fingerprint, strict schema enforcement (additionalProperties: false)

### 3. `docs/contracts/signal.schema.json`
**Why**: JSON Schema v7 contract for trading signals, protected by LR-003 fingerprint, defines side enum (BUY/SELL), rejects legacy fields

### 4. `tests/contract/test_decision_contract.py`
**Why**: 16 deterministic contract tests for risk decision logic, protected by LR-003 fingerprint, validates RC_* reason codes, tests hierarchical ordering

### 5. `services/risk/models.py`
**Why**: Defines Order, Alert, RiskState dataclasses, core risk decision contracts, used across Risk/Execution/Allocation services

### 6. `services/risk/README.md`
**Why**: Documents 5-layer risk decision logic (Circuit Breaker → Position Size → Exposure → Anomaly → Validation), fail-closed principles, risk limits configuration

### 7. `governance/DELIVERY_APPROVED.yaml`
**Why**: Human-controlled delivery approval gate (Constitution §4.2), enforced via CI workflow, exception labels for bypass

### 8. `docs/live-readiness/LR-TASKS.yaml`
**Why**: Single source of truth for LR task manifest (immutable task_id, append-only), defines which tasks exist (LR-001 through LR-007)

### 9. `infrastructure/database/schema.sql`
**Why**: PostgreSQL schema with CHECK constraints, runtime enforcement of invariants (signal_type enum, confidence range, size > 0), fail-closed at DB layer

### 10. `docs/live-readiness/LR-006-EVIDENCE.md`
**Why**: Decision trace contract specification, defines replay-verifiable format (trace_id, input_set, version_set, constraint_set), deterministic traceability for order/lifecycle/parameter decisions

---

## Summary

This inventory identifies **comprehensive governance framework** with:
- **7 Live-Readiness tasks** (6 DONE, 1 BLOCKED)
- **6 core services** with deterministic contracts
- **16+ policy-as-code enforcement mechanisms** (schemas, tests, drift guards, CI gates)
- **559 total tests** (unit, integration, contract)
- **5-layer risk decision logic** with fail-closed design
- **SHA256 fingerprint protection** for critical contracts
- **PostgreSQL CHECK constraints** for runtime invariant enforcement
- **Docker healthcheck ordering** for service dependency management

**Key Strengths**:
- Strong governance foundation (META-001, LR-001 through LR-006)
- Comprehensive contract protection (LR-003 fingerprint, drift guards)
- Deterministic decision logic (risk 5-layer hierarchy, RC_* reason codes)
- Multi-layer enforcement (CI workflows, DB constraints, healthchecks)

**Key Gaps**:
- LR-007 Shadow Mode validation (BLOCKED)
- Paper trading validation incomplete (72-hour soak test pending)
- ML model governance deferred (M5-M9)
- Limited contract drift coverage (only 4 protected files)
- No SLO runtime enforcement gates

**Next Actions**:
1. Complete paper trading validation (unblock LR-007)
2. Execute 72-hour shadow mode soak test
3. Expand LR-003 fingerprint coverage to all service contracts
4. Implement automated decision trace generation (LR-006)
5. Define agent autonomy boundaries and write-gate policy
