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
