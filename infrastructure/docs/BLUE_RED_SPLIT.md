# CDB Blue/Red Stack Architecture

**Version:** 1.0
**Date:** 2026-01-29
**Status:** Implemented & Verified

---

## TL;DR

CDB is split into **BLUE** (Always-On Core) and **RED** (Optional Signals+Monitoring).

**Why:** Risk service **hard-depends** on Allocation + Regime (evidenced file:line). Splitting enables:
- Minimal core that must never fail (BLUE)
- Optional monitoring/signals that can crash without breaking trading (RED)

**Evidence:** `services/risk/service.py:566,888,1019` - allocation_pct <= 0 blocks all orders.

---

## Architecture Decision

### Evidence-Based Split (Not Arbitrary)

**Verification Method:** Direct code analysis

**Critical Dependencies Found:**

1. **services/risk/service.py:566-568**
   ```python
   if state.allocation_pct <= 0:
       return False, "Keine Allokation"  # BLOCKS ORDER
   ```

2. **services/risk/service.py:888**
   ```python
   quantity, skip_reason = self.calculate_position_size(
       signal, allocation.allocation_pct  # qty=0 if allocation_pct=0
   )
   ```

3. **services/risk/service.py:588-639**
   - Risk actively consumes `stream.allocation_decisions`
   - Risk actively consumes `stream.regime_signals`
   - Regime `HIGH_VOL_CHAOTIC` blocks orders (line 604)

**Conclusion:** Allocation + Regime are **core dependencies**, not optional monitoring.

---

## Service Mapping

### BLUE Stack (Always-On Core)

| Service | Layer | Reason |
|---------|-------|--------|
| `cdb_postgres` | Data | Core persistence |
| `cdb_redis` | Data | Message bus + state |
| `cdb_candles` | Control | Data source for Regime (technical indicators) |
| `cdb_regime` | Control | Risk consumes `stream.regime_signals` (L588-610) |
| `cdb_allocation` | Control | Risk blocks orders if `allocation_pct <= 0` (L566) |
| `cdb_risk` | Core | Position sizing depends on allocation (L888) |
| `cdb_execution` | Core | Order execution |
| `cdb_db_writer` | Core | Persistence layer |
| `cdb_paper_runner` | Core | Paper trading state management |

**Dependencies:** BLUE has **no** dependencies on RED.

**Compose File:** `infrastructure/compose/compose.blue.yml`

---

### RED Stack (Optional)

| Service | Layer | Reason |
|---------|-------|--------|
| `cdb_ws` | Signal | Market data ingestion (can be replaced by manual injection) |
| `cdb_signal` | Signal | Signal generation (optional - risk accepts manual signals) |
| `cdb_prometheus` | Monitoring | Metrics collection |
| `cdb_grafana` | Monitoring | Dashboards |
| `cdb_postgres_exporter` | Monitoring | DB metrics |
| `cdb_redis_exporter` | Monitoring | Redis metrics |
| `cdb_cadvisor` | Monitoring | Container metrics |
| `cdb_reports` | Reporting | Daily summaries |

**Dependencies:** RED may depend on BLUE (e.g., ws → redis), but BLUE never depends on RED.

**Compose File:** `infrastructure/compose/compose.red.yml`

---

### Removed Services

| Service | Reason |
|---------|--------|
| `cdb_loki` | Not in current compose (already removed) |
| `cdb_promtail` | Not in current compose (already removed) |
| `cdb_node_exporter` | Removed from active BLUE+RED runtime canon; Windows/WSL2 mount propagation issues and no supported host node-exporter surface in current stack |

---

## Network Architecture

**Shared Network:** `cdb_network` (Docker bridge, external)

**Lifecycle:**
1. Create once: `docker network create cdb_network`
2. BLUE attaches to network
3. RED attaches to same network
4. Services communicate via service names (e.g., `cdb_redis:6379`)

**Isolation:**
- Each stack has independent lifecycle (start/stop/restart)
- RED can crash/restart without affecting BLUE
- No shared volumes between stacks

---

## Operational Model

### Startup Sequence

```powershell
# One-time setup
docker network create cdb_network

# Start Core (mandatory)
docker compose -f infrastructure/compose/compose.blue.yml up -d

# Verify Core Flow (gate)
python scripts/smoke_core_flow.py

# Start Monitoring (optional)
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### Automated Setup

```powershell
# Full stack (BLUE + RED)
.\infrastructure\scripts\setup_blue_red.ps1

# Core only (for manual signal testing)
.\infrastructure\scripts\setup_blue_red.ps1 -SkipRed

# Skip smoke test (for faster iteration)
.\infrastructure\scripts\setup_blue_red.ps1 -SkipSmokeTest
```

---

## Testing & Verification

### Smoke Test (E2E Gate)

**Purpose:** Prove core flow works: Signal → Risk → Execution → DB

**Method:**
1. Inject deterministic signal with `strategy_id=paper` (has allocation)
2. Wait 8s for propagation
3. Verify:
   - Redis: `stream.order_results` contains order
   - Postgres: `orders` + `trades` tables have rows
4. Generate report: `reports/CORE_FLOW_E2E_SMOKE.md`

**Usage:**
```powershell
.\infrastructure\scripts\smoke_test.ps1
```

**Exit Codes:**
- `0` = PASS (core flow operational)
- `1` = FAIL (see report for diagnosis)

---

## Failure Modes

### BLUE Stack Failure

**Impact:** Trading stops completely.

**Recovery:**
1. Check service health: `docker compose -f infrastructure/compose/compose.blue.yml ps`
2. Check allocation: `curl http://localhost:8002/status | jq .allocation_state`
3. Review logs: `docker compose -f infrastructure/compose/compose.blue.yml logs cdb_risk cdb_allocation cdb_regime`
4. Run smoke test: `.\infrastructure\scripts\smoke_test.ps1`

### RED Stack Failure

**Impact:** No signals generated, no monitoring, but manual trading still possible.

**Recovery:**
1. BLUE continues operating (verify with smoke test using manual injection)
2. Fix RED issue independently
3. Restart RED: `docker compose -f infrastructure/compose/compose.red.yml restart`

---

## Migration from Legacy Compose

**Legacy (CI-only):** `base.yml + dev.yml` remain for CI/test workflows
(e.g., `shadow-soak-evidence.yml`, `e2e.yml`). They are not the normal
operator runtime path.

**Canonical runtime:** BLUE+RED via `setup_blue_red.ps1` or manual
`docker compose -f infrastructure/compose/compose.blue.yml up -d`.

**Differences from the old single-stack layout:**
- Network must be created manually once
- Two separate compose projects (independent lifecycles)
- Explicit dependency management (no hidden coupling)
- Lower log verbosity in BLUE (INFO vs DEBUG)

---

## Network Cutover (Issue #1210)

**Symptom:** BLUE services land on `claire_de_binare_cdb_network` instead of
`cdb_network` when the stack was previously started via `base.yml + dev.yml`.

**Root cause:** `base.yml` defines `cdb_network` as an internal bridge; Docker
auto-prefixes the project name → `claire_de_binare_cdb_network`. The canonical
`compose.blue.yml` declares `cdb_network` as `external: true` — requires the
network to exist before stack start.

**Detection:**
```powershell
docker inspect cdb_allocation | Select-String "claire_de_binare"
# Empty output = on cdb_network (correct)
# "claire_de_binare_cdb_network" in output = legacy network (needs cutover)
```

**Cutover procedure (low risk, brief outage):**
```powershell
# 1. Ensure cdb_network exists
docker network create cdb_network

# 2. Force-recreate BLUE to attach to correct network
docker compose -f infrastructure/compose/compose.blue.yml up -d --force-recreate

# 3. Verify
docker inspect cdb_allocation cdb_candles cdb_db_writer cdb_paper_runner cdb_regime \
  | Select-String "NetworkMode|cdb_network|claire_de_binare"

# 4. Restart RED to ensure it can reach BLUE services
docker compose -f infrastructure/compose/compose.red.yml up -d --force-recreate
```

**After cutover:** `make docker-up` / `make docker-down` use canonical BLUE+RED
paths and will no longer trigger this drift.

---

## Rationale for Design Choices

### Why Not Blue-Green Deployment?

Blue/Red here is **not** blue-green deployment (parallel production+staging). It's a **functional split**:
- BLUE = core trading (must be stable)
- RED = optional features (can fail independently)

### Why Allocation + Regime in BLUE?

**Alternative considered:** Move to RED, bootstrap from Redis on startup.

**Rejected because:**
- Risk blocks orders immediately if allocation=0 (no fallback)
- Regime `HIGH_VOL_CHAOTIC` is safety-critical (blocks risky trades)
- Bootstrap is complex and error-prone (state synchronization)

**Evidence wins:** Code analysis shows hard dependency, not optional monitoring.

### Why Signal in RED?

**Alternative considered:** Signal in BLUE (always-on signal generation).

**Chosen RED because:**
- Manual signal injection is possible (smoke test proves this)
- Signal is a data source, not a decision-maker
- Allows testing risk logic in isolation
- Reduces BLUE complexity

---

## Future Enhancements

1. **Correlation ID:** Add `correlation_id` field to Signal schema for end-to-end tracking
2. **Health Dashboard:** Dedicated BLUE health check endpoint (consolidated status)
3. **Auto-Scaling RED:** Scale signal/monitoring independently from core
4. **Backtest Service:** Add backtest to RED (mentioned in requirements, not yet implemented)

---

## References

- **Compose Files:**
  - `infrastructure/compose/compose.blue.yml`
  - `infrastructure/compose/compose.red.yml`
- **Scripts:**
  - `infrastructure/scripts/setup_blue_red.ps1`
  - `infrastructure/scripts/smoke_test.ps1`
  - `scripts/smoke_core_flow.py`
- **Evidence:**
  - `services/risk/service.py:566,888,1019` (allocation dependency)
  - `services/risk/service.py:588-639` (regime stream consumption)
