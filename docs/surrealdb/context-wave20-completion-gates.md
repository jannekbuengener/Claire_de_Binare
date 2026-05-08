# Wave-20 Completion Gates

**Wave:** 20  
**Anchor:** #2188 (close after merge + separate GO GITHUB LIVE)  
**Children:** #2191, #2192, #2193, #2194, #2195, #2196  
**Epic:** #1976  
**Live-Readiness:** `NO-GO` — no real trades, no Echtgeld, no LR-Go  
**Board Stage:** `trade-capable` (ratified 2026-04-08 via #1492) — orthogonal to LR

---

## Completion Gates

All gates must be `✅` before the Wave-20 PR is ready to merge.

### G1 — Evaluator exists and passes lint

```bash
python -c "import tools.surrealdb.agent_os_readiness; print('import ok')"
ruff check tools/surrealdb/agent_os_readiness.py
```

- [ ] `tools/surrealdb/agent_os_readiness.py` exists
- [ ] Import succeeds
- [ ] Ruff: zero violations

---

### G2 — Evaluator produces result from minimal bundle

```python
from tools.surrealdb.agent_os_readiness import evaluate_agent_os_readiness_v1
result = evaluate_agent_os_readiness_v1(
    {"meta": {"scope_id": "gate-check"}},
    as_of="2026-05-08T12:00:00+00:00"
)
assert result.readiness_level in {"blocked", "weak", "acceptable", "strong"}
```

- [ ] Returns `AgentOsReadinessResult` without raising

---

### G3 — `readiness_id` is deterministic (SHA-256)

```python
r1 = evaluate_agent_os_readiness_v1(bundle, as_of=ts)
r2 = evaluate_agent_os_readiness_v1(bundle, as_of=ts)
assert r1.readiness_id == r2.readiness_id
assert len(r1.readiness_id) == 16
```

- [ ] Same inputs → same `readiness_id`
- [ ] ID is 16-character hex string

---

### G4 — Guardrails always 5 non-empty items

```python
assert len(result.guardrails) == 5
assert all(isinstance(g, str) and g.strip() for g in result.guardrails)
```

- [ ] Every result has exactly 5 guardrails
- [ ] No empty or whitespace-only guardrails

---

### G5 — `"blocked"` level on blocking quality / scope-drift / contradiction / stale finding

```python
# Blocking scope drift → blocked
bundle["scope_drift_findings"] = [{"drift_id": "x", "severity": "blocking", "status": "open", ...}]
assert evaluate_agent_os_readiness_v1(bundle).readiness_level == "blocked"
```

- [ ] Blocking quality grade → `blocked`
- [ ] Blocking scope drift finding → `blocked`
- [ ] Blocking contradiction finding → `blocked`
- [ ] `source_deleted` stale finding → `blocked`

---

### G6 — `"strong"` level on clean bundle

```python
result = evaluate_agent_os_readiness_v1(clean_bundle)
assert result.readiness_level == "strong"
assert result.confidence >= 0.90
```

- [ ] Clean bundle → `readiness_level == "strong"`
- [ ] Clean bundle → `confidence ≥ 0.90`

---

### G7 — `AgentOsReadinessError` on invalid bundle

```python
with pytest.raises(AgentOsReadinessError):
    evaluate_agent_os_readiness_v1(None)
with pytest.raises(AgentOsReadinessError):
    evaluate_agent_os_readiness_v1({"meta": {}})   # missing scope_id
```

- [ ] `None` bundle → `AgentOsReadinessError`
- [ ] Non-mapping bundle → `AgentOsReadinessError`
- [ ] Missing `meta.scope_id` → `AgentOsReadinessError`

---

### G8 — MCP adapter exists and passes lint

```bash
python -c "import tools.mcp.agent_os_readiness_tools; print('import ok')"
ruff check tools/mcp/agent_os_readiness_tools.py
```

- [ ] `tools/mcp/agent_os_readiness_tools.py` exists
- [ ] Import succeeds
- [ ] Ruff: zero violations

---

### G9 — MCP adapter fail-closed for missing/invalid bundle

```python
from tools.mcp.agent_os_readiness_tools import handle_agent_os_readiness
r = handle_agent_os_readiness()
assert r["status"] == "error" and r["error"]["code"] == "missing_bundle"
r = handle_agent_os_readiness(bundle="not-a-dict")
assert r["status"] == "error" and r["error"]["code"] == "invalid_bundle"
```

- [ ] Missing bundle → `status="error"`, `code="missing_bundle"`
- [ ] Non-dict bundle → `status="error"`, `code="invalid_bundle"`
- [ ] All error responses include `guardrails`

---

### G10 — Registry contains `cdb_agent_os_readiness` with `read_only=True`

```python
from tools.mcp.registry import ContextToolRegistry
tool = ContextToolRegistry.get_tool("cdb_agent_os_readiness")
assert tool is not None
assert tool.read_only is True
```

- [ ] Tool registered in `ContextToolRegistry`
- [ ] `read_only == True`
- [ ] `assert_read_only_consistency()` passes after `ContextBridge.__init__`

---

### G11 — `PermissionGuard` exempt list includes `cdb_agent_os_readiness`

```python
from tools.mcp.permission_guard import INPUT_SCAN_EXEMPT_TOOLS
assert "cdb_agent_os_readiness" in INPUT_SCAN_EXEMPT_TOOLS
```

- [ ] Tool in `INPUT_SCAN_EXEMPT_TOOLS`

---

### G12 — All Wave-20 unit tests pass

```bash
pytest -q tests/unit/surrealdb/test_agent_os_readiness.py
pytest -q tests/unit/tools/mcp/test_agent_os_readiness_tools.py
```

- [ ] `test_agent_os_readiness.py` — all tests pass (target ≥ 38 tests)
- [ ] `test_agent_os_readiness_tools.py` — all tests pass (target ≥ 25 tests)
- [ ] Full surrealdb suite unbroken: `pytest -q tests/unit/surrealdb/`
- [ ] Full MCP suite unbroken: `pytest -q tests/unit/tools/mcp/`

---

### G13 — No file I/O, DB, network, or mutations in evaluation path

- [ ] `evaluate_agent_os_readiness_v1` contains no `open()`, `socket`, DB SDK calls
- [ ] `handle_agent_os_readiness` contains no writes, no `open()`, no DB SDK calls
- [ ] `test_no_socket_connection_is_attempted` test passes (monkeypatched)

---

### G14 — Guardrails include all required no-go statements

Every `AgentOsReadinessResult.guardrails` tuple must contain:

- [ ] `"No trading console"` (exact substring)
- [ ] `"No Live-Readiness-Go"` (exact substring)
- [ ] `"No Echtgeld-Go"` (exact substring)
- [ ] `"read-only"` (exact substring)
- [ ] Signal-not-authorization statement (`"Agent OS Readiness is a signal"`)
- [ ] Human-GO statement (`"Human-GO required"`)

---

### G15 — Runbook and fixture published

- [ ] `docs/surrealdb/context-wave20-agent-os-readiness-runbook.md` exists
- [ ] Runbook contains "Readiness Signal ≠ Live-Go" section
- [ ] Runbook contains guardrails section
- [ ] `tests/fixtures/surrealdb/agent_os_readiness/sample_bundle.json` exists

---

## Issue-Level Gates

### #2191 — Agent OS readiness evaluator

- [ ] `evaluate_agent_os_readiness_v1` public API exists
- [ ] All 5 sub-evaluators wired: quality, scope_drift, contradictions, stale, architect_signals
- [ ] `readiness_id` deterministic
- [ ] `READINESS_LEVELS` constant defined
- [ ] `GUARDRAILS` constant (5 items) defined

### #2192 — Agent OS readiness MCP tool

- [ ] `handle_agent_os_readiness` exists in `tools/mcp/agent_os_readiness_tools.py`
- [ ] Tool name `cdb_agent_os_readiness` registered in registry
- [ ] Handler wired in `ContextBridge.__init__` (Wave-20 handler map)
- [ ] Tool in `INPUT_SCAN_EXEMPT_TOOLS`
- [ ] `assert_read_only_consistency()` passes

### #2193 — Agent OS readiness report

- [ ] `AgentOsReadinessResult.to_report_markdown()` method exists and returns str
- [ ] `handle_agent_os_readiness(include_report=True)` returns `report_markdown` key
- [ ] Report contains scope_id, readiness level, guardrails, NO-GO statement

### #2194 — Tests

- [ ] `tests/unit/surrealdb/test_agent_os_readiness.py` — ≥ 38 tests
- [ ] `tests/unit/tools/mcp/test_agent_os_readiness_tools.py` — ≥ 25 tests
- [ ] `tests/fixtures/surrealdb/agent_os_readiness/sample_bundle.json` — valid JSON
- [ ] All new tests marked `@pytest.mark.unit` (via module-level `pytestmark`)
- [ ] Tests cover: blocked/weak/acceptable/strong, error cases, determinism, guardrails, no-side-effects

### #2195 — Runbook

- [ ] `docs/surrealdb/context-wave20-agent-os-readiness-runbook.md` published
- [ ] Documents readiness levels, input bundle shape, output fields, usage examples
- [ ] Explicit guardrails section
- [ ] Explicit "Readiness Signal ≠ Live-Go" section with LR: NO-GO statement

### #2196 — Completion gates (this file)

- [ ] `docs/surrealdb/context-wave20-completion-gates.md` published
- [ ] G1–G15 defined with validation commands
- [ ] Issue-level gates #2191–#2196 defined
- [ ] Non-goals section present

---

## PR Gate

The Wave-20 PR must contain **exactly these files**:

| File | Type |
|---|---|
| `tools/surrealdb/agent_os_readiness.py` | new |
| `tools/mcp/agent_os_readiness_tools.py` | new |
| `tests/unit/surrealdb/test_agent_os_readiness.py` | new |
| `tests/unit/tools/mcp/test_agent_os_readiness_tools.py` | new |
| `tests/fixtures/surrealdb/agent_os_readiness/sample_bundle.json` | new |
| `docs/surrealdb/context-wave20-agent-os-readiness-runbook.md` | new |
| `docs/surrealdb/context-wave20-completion-gates.md` | new |
| `tools/mcp/registry.py` | modified |
| `tools/mcp/permission_guard.py` | modified |
| `tools/mcp/context_bridge.py` | modified |

**Total: 10 files** (7 new, 3 modified)

---

## Post-Merge Closure Order

After PR merge and separate GO GITHUB LIVE:

1. Close #2191 — evaluator
2. Close #2192 — MCP tool
3. Close #2193 — report
4. Close #2194 — tests
5. Close #2195 — runbook
6. Close #2196 — completion gates (this file)
7. Close #2188 — Wave-20 anchor (last)

---

## Non-Goals

- No Live-Readiness-Go (LR remains `NO-GO`)
- No Echtgeld-Go, no real trading, no live capital
- No changes to `services/risk/`, `services/execution/`, `core/safety/`
- No changes to `governance/DELIVERY_APPROVED.yaml`
- No new issues created in this wave
- No auto-action on any readiness signal
- No DB writes, no SurrealDB SDK calls
- No Wave-21 work
