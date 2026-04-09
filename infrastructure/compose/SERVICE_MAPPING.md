# CDB Compose Files - Service Mapping

**Architecture:** Blue/Red Split (Evidence-Based)
**Date:** 2026-01-29

---

## Quick Reference

| Stack | Compose File | Purpose | Can Fail? |
|-------|--------------|---------|-----------|
| **BLUE** | `compose.blue.yml` | Core Trading (Always-On) | ❌ No |
| **RED** | `compose.red.yml` | Signals + Monitoring (Optional) | ✅ Yes |

---

## Service Mapping

### BLUE Stack (Always-On Core)

| Service | Port | Layer | Hard Dependency | Evidence |
|---------|------|-------|-----------------|----------|
| `cdb_postgres` | 5432 | Data | - | Core persistence |
| `cdb_redis` | 6379 | Data | - | Message bus + state |
| `cdb_candles` | 8007 | Control | Redis | Input for Regime (technical indicators) |
| `cdb_regime` | 8008 | Control | Redis, Candles | Risk consumes `stream.regime_signals` (risk/service.py:588) |
| `cdb_allocation` | 8006 | Control | Redis | Risk blocks if `allocation_pct <= 0` (risk/service.py:566) |
| `cdb_risk` | 8002 | Core | Postgres, Redis, Allocation, Regime | Position sizing uses allocation (risk/service.py:888) |
| `cdb_execution` | 8003 | Core | Postgres, Redis | Order execution |
| `cdb_db_writer` | - | Core | Postgres, Redis | Persistence layer |
| `cdb_paper_runner` | 8004 | Core | Postgres, Redis | Paper trading runner |

**Total:** 9 services
**Must Be Healthy:** All (except db_writer has process-only healthcheck)

---

### RED Stack (Optional)

| Service | Port | Layer | Hard Dependency | Can Replace With |
|---------|------|-------|-----------------|------------------|
| `cdb_ws` | 8000 | Signal | Redis | Manual signal injection |
| `cdb_signal` | 8005 | Signal | Redis, WS | Manual signal injection |
| `cdb_prometheus` | 19090 | Monitoring | - | N/A (monitoring optional) |
| `cdb_grafana` | 3000 | Monitoring | Prometheus | N/A (monitoring optional) |
| `cdb_postgres_exporter` | 9187 | Monitoring | - | N/A (metrics optional) |
| `cdb_redis_exporter` | 9121 | Monitoring | - | N/A (metrics optional) |
| `cdb_cadvisor` | - | Monitoring | - | N/A (metrics optional) |
| `cdb_reports` | - | Reporting | Postgres | N/A (reports optional) |

**Total:** 8 services
**Can Fail:** Yes (BLUE continues operating)

---

## Removed Services

| Service | Reason | Alternative |
|---------|--------|-------------|
| `cdb_loki` | Not in current compose | Removed earlier |
| `cdb_promtail` | Not in current compose | Removed earlier |
| `cdb_node_exporter` | Removed from active BLUE+RED runtime canon due to Windows/WSL2 mount propagation issues | cAdvisor for container metrics; no host node-exporter metrics in current canon |

---

## Evidence Summary

### Why Allocation + Regime in BLUE?

**File:** `services/risk/service.py`

**Line 566-568:** Blocks orders if allocation_pct <= 0
```python
def _allocation_allowed(self, strategy_id: str) -> tuple[bool, str]:
    state = self._get_allocation_state(strategy_id)
    if state.allocation_pct <= 0:
        return False, "Keine Allokation"  # BLOCKS ORDER
```

**Line 888:** Position sizing uses allocation
```python
quantity, skip_reason = self.calculate_position_size(
    signal, allocation.allocation_pct  # qty=0 if allocation_pct=0
)
```

**Line 588-639:** Active stream consumption
```python
def _listen_allocation_stream(self):
    # Risk actively reads stream.allocation_decisions
    response = self.redis_client.xread({self.config.allocation_stream: last_id}, ...)

def _listen_regime_stream(self):
    # Risk actively reads stream.regime_signals
    # HIGH_VOL_CHAOTIC blocks new positions
```

**Conclusion:** Allocation + Regime are **not** monitoring - they're decision inputs that directly block orders.

---

## Network Architecture

```
┌─────────────────────────────────────────┐
│          Docker Network: cdb_network    │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────── BLUE Stack ────────┐       │
│  │  postgres  redis            │       │
│  │  candles  regime  allocation│       │
│  │  risk  execution  db_writer │       │
│  │  paper_runner               │       │
│  └─────────────────────────────┘       │
│                                         │
│  ┌───────── RED Stack ─────────┐       │
│  │  ws  signal                 │       │
│  │  prometheus  grafana        │       │
│  │  exporters  reports         │       │
│  └─────────────────────────────┘       │
│                                         │
└─────────────────────────────────────────┘
```

**Communication:** Service names (e.g., `cdb_redis:6379`)
**Isolation:** Independent compose projects (can start/stop separately)

---

## Reference Documentation

- **Architecture:** `infrastructure/docs/BLUE_RED_SPLIT.md`
- **Quick Start:** `infrastructure/docs/QUICK_START.md`
- **Smoke Test:** `scripts/README_SMOKE_TEST.md`
