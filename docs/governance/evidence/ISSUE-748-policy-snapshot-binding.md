# Evidence Spec for Issue #748 — Policy Snapshot Binding: policy hash/version in ledger events
Purpose:
- Define a docs-only evidence contract for how implementation proof for policy snapshot binding should be collected and linked in Issue #748.
- Ensure future implementation work can add auditable evidence without changing the issue structure again.

Pass criteria:
- [ ] At least one implementation PR is linked that introduces or updates `policy_id` / hash / version binding for relevant events.
- [ ] At least one CI run or validation run is linked and attributable to the implementation PR(s).
- [ ] At least one spec/ADR/docs reference is linked that documents the intended binding behavior and compatibility expectations.

Evidence plan:
- Expected PR(s): policy snapshot binding implementation PR(s) referencing #748.
- Expected CI runs: workflow runs validating tests/linting for the implementation PR(s), plus any focused validation job if present.
- Expected docs/ADRs: spec/ADR/docs that describe policy hash/version binding, anti-drift intent, and event/ledger linkage.

Current status:
- **Slice 1 implemented.** Date: 2026-02-24

---

## Slice 1: Optional `policy_snapshot` Field

**Scope:** Additive, offline/replay-only schema preparation. No runtime/trading impact.

### What Was Changed

| File | Change |
|------|--------|
| `core/replay/envelopes.py` | Added `policy_snapshot: Optional[Dict[str, Any]] = None` to all 3 envelope dataclasses + conditional `to_dict()` emission |
| `core/replay/emitter.py` | Added `policy_snapshot` param to `_build_envelope()` + all 3 `emit_*` functions (default None, conditional emission) |
| `tests/unit/replay/test_envelopes.py` | +4 tests: omit-when-None assertions, include-when-set, determinism with snapshot |

### Schema

`policy_snapshot` is an optional nested dict with suggested fields:

| Field | Type | Description |
|-------|------|-------------|
| `policy_id` | string | Policy identifier |
| `policy_version` | string | Semantic version |
| `git_commit` | string | Git commit hash of policy source |
| `checksum` | string | Deterministic checksum of policy content |
| `effective_at` | string | ISO 8601 timestamp of when policy became effective |

All fields are free-form strings. The dict is opaque to the replay framework — no validation of inner fields.

### Guardrails

| Guardrail | How |
|-----------|-----|
| No golden hash drift | `to_dict()` omits `policy_snapshot` when None; existing fixtures byte-identical |
| No runtime impact | Default None; emitter toggle gate unchanged; no service hooks modified |
| Backward compatible | Optional field with default None; no new required fields |
| Deterministic | `canonical_json_dumps()` handles nested dicts via `sort_keys=True` |

### Test Evidence

- 63/63 replay tests green (7 existing envelope + 4 new snapshot + 22 emitter + 30 replay)
- Golden file hashes unchanged (`test_replay_matches_golden_hashes`, `test_golden_canonical_bytes_stability`)

## Merge Outcome / Audit Note

- PR: #960
- Merge method: merge commit (Auto-Merge), squash not permitted by repository ruleset
- Merge commit: 482170a
- Reason: head branch required up-to-date with main; required conversation resolution; CI green; auto-merge executed

---

## Slice 2: Runtime Wiring for `policy_snapshot` Binding

**Scope:** Toggle-gated runtime wiring. Populates `policy_snapshot` on Decision/Order/Fill envelopes when `CDB_POLICY_SNAPSHOT_BINDING_ENABLED=1`. No trading logic changes.

### What Was Changed

| File | Change |
|------|--------|
| `core/replay/policy_snapshot.py` | NEW: `build_policy_snapshot()` builder + `policy_snapshot_binding_enabled()` toggle |
| `services/risk/models.py` | Added `policy_snapshot: Optional[dict] = None` to `Order` dataclass + conditional `to_dict()` emission |
| `services/execution/models.py` | Added `policy_snapshot` field to `Order` + `from_event()` deserialization via `_parse_json_field()` + conditional `to_dict()` |
| `services/risk/service.py` | Wiring: build snapshot after `_phase9_enrich_evidence()` → pass to decision/order envelopes + Order constructor |
| `services/execution/service.py` | Wiring: pass `policy_snapshot` from Order to fill envelope |
| `tests/unit/replay/test_policy_snapshot.py` | Builder + toggle unit tests (14 tests) |
| `tests/unit/replay/test_policy_snapshot_wiring.py` | Wiring, propagation, Redis roundtrip, zero-change tests (20 tests) |

### Toggle

| Property | Value |
|----------|-------|
| Name | `CDB_POLICY_SNAPSHOT_BINDING_ENABLED` |
| Default | `"0"` (OFF) |
| Independence | Independent of `TRACE_CONTRACT_V1_ENABLED` and `CDB_ENVELOPE_EMISSION` |
| OFF behavior | Zero mutations, zero new fields, existing payloads byte-identical |
| ON behavior | `build_policy_snapshot()` called; snapshot attached to all 3 envelope types via Order propagation |

### Schema (Runtime)

`policy_snapshot` dict fields (all strings):

| Field | Source | Description |
|-------|--------|-------------|
| `policy_id` | `POLICY_ID` constant (`core/utils/uuid_gen.py`) | `"risk_policy_v1"` — primary runtime policy reference |
| `version` | `CDB_POLICY_VERSION` env var, fallback `"unknown"` | No hardcoded value; set in CI/deploy |
| `git_commit` | `CDB_GIT_COMMIT` env var, fallback `"unknown"` | Repo commit at deploy time |
| `checksum` | `compute_policy_hash(DECISION_THRESHOLDS)` | SHA256 of canonical JSON (sorted keys, compact separators) |
| `effective_at` | `deterministic_ts_ms` → ISO-8601 UTC | Signal timestamp, not wall-clock |

### Guardrails

| Guardrail | How |
|-----------|-----|
| No golden hash drift | Toggle OFF = `policy_snapshot` key not emitted anywhere; `to_dict()` conditional emission |
| No trading path breakage | All snapshot code wrapped in `try/except: pass` guardrails |
| Deterministic | Uses `deterministic_ts_ms` (signal timestamp); checksum via stable serialization |
| No secrets | Only policy_id, version, git SHA, hash, timestamp — verified by test |
| Redis roundtrip safe | `sanitize_payload()` serializes dict → JSON string; `_parse_json_field()` deserializes |
| Emission rule | `policy_snapshot` only emitted when toggle ON AND value not None |

### Runtime Invariant

> Toggle ON ⇒ every new Decision has exactly one `policy_snapshot` (not None, not list).
> Toggle OFF ⇒ zero payload change, no `policy_snapshot` key anywhere.

### Query / Acceptance Demo

```
Show DecisionEvent + PolicySnapshot + Evidence chain:

  SELECT
    d.event_id        AS decision_id,
    d.policy_snapshot  ->> 'policy_id'    AS policy_id,
    d.policy_snapshot  ->> 'version'      AS policy_version,
    d.policy_snapshot  ->> 'checksum'     AS policy_checksum,
    d.policy_snapshot  ->> 'git_commit'   AS git_commit,
    d.policy_snapshot  ->> 'effective_at' AS effective_at,
    o.event_id        AS order_id,
    f.event_id        AS fill_id
  FROM decision_envelopes d
  LEFT JOIN order_envelopes o ON o.payload ->> 'decision_id' = d.event_id
  LEFT JOIN fill_envelopes  f ON f.payload ->> 'order_id'    = o.event_id
  WHERE d.policy_snapshot IS NOT NULL  -- Toggle ON only

Join path:
  Decision.event_id = Order.payload.decision_id
  Order.event_id    = Fill.payload.order_id

All three envelopes carry the identical policy_snapshot dict.
```

### Test Evidence

- Builder tests: 14 unit tests (toggle, keys, checksum determinism, secret-free, env vars)
- Wiring tests: 20 tests (toggle OFF zero-change, toggle ON propagation, Redis roundtrip, golden hash stability)

---

## Smoke Runbook: Toggle ON Verification (Staging)

Pre-condition: PR #962 merged (CDB_GIT_COMMIT + CDB_POLICY_VERSION wired in Compose).

### Steps

1. **Enable toggle in staging Compose override** (do NOT commit):
   ```bash
   # Temporary: add to cdb_risk + cdb_execution environment in your staging compose
   CDB_POLICY_SNAPSHOT_BINDING_ENABLED: "1"
   CDB_ENVELOPE_EMISSION: "1"
   ```

2. **Restart risk + execution services** (adjust compose files to your staging overlay):
   ```bash
   docker compose -f base.yml -f <your-staging-overlay>.yml up -d cdb_risk cdb_execution
   ```

3. **Trigger a signal** (paper mode / stub) and wait for Decision→Order→Fill.

4. **Inspect DECISION envelope** (from JSONL log or Redis stream):
   ```bash
   # Example: last DECISION envelope from replay log
   tail -1 logs/replay_envelopes.jsonl | python -m json.tool
   ```

5. **Verify policy_snapshot fields**:

   | Field | Expected (CI/Staging) | Fail if |
   |-------|-----------------------|---------|
   | `policy_id` | `"risk_policy_v1"` | missing or empty |
   | `version` | tag name or `"dev-<7-char-sha>"` | `"unknown"` |
   | `git_commit` | 40-char hex SHA | `"unknown"` |
   | `checksum` | 64-char hex SHA256 | missing or empty |
   | `effective_at` | ISO-8601 with `+00:00` | missing or not UTC |

6. **Verify propagation**: ORDER and FILL envelopes carry the **identical** `policy_snapshot` dict as the DECISION envelope (same `checksum`, same `effective_at`).

7. **Verify zero-drift**: With toggle OFF (default), repeat step 4 — `policy_snapshot` key must NOT appear in any envelope.

### Pass Criteria
- Toggle ON: all 5 fields present, `version` and `git_commit` are NOT `"unknown"` in CI/staging
- Toggle OFF: no `policy_snapshot` key anywhere
- No trading behavior change in either mode
