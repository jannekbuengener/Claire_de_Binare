# P5 Prestart Pack

- Control: `LR-050`
- Status: `NO-GO`
- Last updated: `2026-03-20`

This document is a **template** and **governance anchor** for the P5 canary prestart evidence lock.
It does **not** authorize a canary start. Start remains blocked until all NO-GO blockers are resolved.

It backs the following compensating controls defined in `governance/p5_canary_readiness.yaml`:
- `prestart_evidence_lock`
- `canonical_runtime_mode_precheck`
- `decision_record_before_start`
- `no_code_or_config_change_after_prestart_lock`

Normative rule from `governance/p5_canary_readiness.yaml` for the current P5 / shadow-prereq path:
- canonical runtime-mode field = `execution_status.mode`
- required value = `mock`
- `shadow` = probe / intent / evidence semantics only
- `full|lean` = soak / collection profile labels only

---

## 1. Current Status

**Status: NO-GO**

Open blockers (must all resolve before any P5 start attempt):

| Blocker | Required | Current State |
|---------|----------|---------------|
| LR-040 72h Soak PASS | YES | IMPLEMENTED — no 72h run evidence yet |
| Committed P5 canary run artifact set | YES | None exists |

Until both blockers are resolved, this template has no operative function.
No section of this document authorizes, enables, or implies approval for a live canary start.

---

## 2. Stack Anchor

The shadow-mode and prestart context runs on the **BLUE stack**:

- Compose file: `infrastructure/compose/compose.blue.yml`
- cdb_risk: `http://127.0.0.1:8002` — kill-switch endpoint + risk `/status`
- cdb_execution: `http://127.0.0.1:8003` — execution `/status` (mode field)

RED (`infrastructure/compose/compose.red.yml`) = signal generation + monitoring. Optional, separable.
RED is not a prestart gate anchor. Abort and stop are always anchored on BLUE.

---

## 3. Prestart Evidence Capture (`prestart_evidence_lock`)

When all blockers are resolved, the operator captures and commits the following before any start.
Fill in all placeholders. A blank or missing field constitutes a gate failure.

```yaml
evidence_lock_utc: <YYYY-MM-DDTHH:MM:SSZ>

commit_sha: <output of: git rev-parse HEAD>
worktree_status: clean  # git status --porcelain must return empty

kill_switch_status:
  active: false          # REQUIRED: must be false
  source: http://127.0.0.1:8002/kill-switch
  captured_utc: <YYYY-MM-DDTHH:MM:SSZ>
  response: <full JSON response>

execution_status:
  mode: mock             # REQUIRED: must be "mock"
  source: http://127.0.0.1:8003/status
  captured_utc: <YYYY-MM-DDTHH:MM:SSZ>
  response: <full JSON response>

risk_status:
  circuit_breaker: false # REQUIRED: must be false
  source: http://127.0.0.1:8002/status
  captured_utc: <YYYY-MM-DDTHH:MM:SSZ>
  response: <full JSON response>

artifact_path: reports/p5_canary/<YYYY-MM-DD>/
operator: <name>
```

### P5 Core Artifact Contract

Committed P5 core artifacts are rooted at:

```text
reports/p5_canary/<YYYY-MM-DD>/
```

Required committed files:

- `manifest.json`
- `prestart_evidence_lock.yaml`
- `decision_record.yaml`
- `endpoints/execution_status.json`
- `endpoints/risk_status.json`
- `endpoints/kill_switch_status.json`
- `lr040/lr040_soak_gate_eval.json`

The files `prestart_evidence_lock.yaml` and `decision_record.yaml` are the committed operator-facing records.
The files under `endpoints/` are the raw endpoint snapshots captured for the same evidence lock.

Optional reused shadow-prereq evidence:

- `shadow_prereq/manifest.json`
- `shadow_prereq/package_manifest.json`

Minimum fields for `manifest.json`:

- `schema_version`
- `package_type`
- `package_status`
- `commit_sha`
- `artifact_root`
- `execution_runtime_mode`
- `evidence_lock_path`
- `decision_record_path`
- `endpoint_snapshots`
- `lr040_verdict_path`
- `optional_shadow_prereq_package`
- `checksums`

Capture commands (run from repo root, BLUE stack must be up):

```bash
# Commit and worktree
git rev-parse HEAD
git status --porcelain

# Kill-switch (cdb_risk, BLUE, Port 8002)
curl -s http://127.0.0.1:8002/kill-switch

# Execution mode (cdb_execution, BLUE, Port 8003)
curl -s http://127.0.0.1:8003/status

# Risk status (cdb_risk, BLUE, Port 8002)
curl -s http://127.0.0.1:8002/status
```

---

## 4. Freeze Declaration (`no_code_or_config_change_after_prestart_lock`)

After `evidence_lock_utc` is set:

- No code commits
- No config changes (compose files, env vars, secrets)
- No stack rebuild or image pull
- Exception: kill-switch activation (abort path, see §6)

Any change after evidence-lock invalidates the lock. A new lock capture is required before retry.

---

## 5. Decision Record (`decision_record_before_start`)

Operator fills and commits this before any start attempt. Required even if status is NO-GO.

```yaml
decision_utc: <YYYY-MM-DDTHH:MM:SSZ>
operator: <name>
lr040_pass_run_id: <GitHub Actions Run ID>
lr040_pass_commit: <SHA>
canary_artifact_path: reports/p5_canary/<YYYY-MM-DD>/
status: GO | NO-GO
rationale: >
  <Freitext — warum GO oder NO-GO. Bei NO-GO: welcher Blocker verbleibt.>
```

A `status: NO-GO` decision record is valid and expected during the current phase.
A `status: GO` decision record is only valid after both blockers in §1 are resolved.

---

## 6. Abort / Stop / Rollback

All commands anchored on BLUE stack. Run from repo root.

### Abort (kill-switch, immediate — use even during an active run)

```bash
# Activate kill-switch (cdb_risk, BLUE, Port 8002)
curl -s -X POST http://127.0.0.1:8002/kill-switch/activate \
  -H "Content-Type: application/json" \
  -d '{"reason":"operator_abort","message":"P5 abort","operator":"<name>"}'

# Verify active
curl -s http://127.0.0.1:8002/kill-switch
# Expected: "active": true
```

### Stop stack

```bash
# Stop BLUE stack (primary — prestart context)
docker compose -f infrastructure/compose/compose.blue.yml down

# Stop RED stack (optional — monitoring/signal, if running)
# Order: RED first, then BLUE
docker compose -f infrastructure/compose/compose.red.yml down
```

### Rollback

```bash
# Use commit_sha from evidence_lock (§3) as the known-good anchor
git checkout <commit_sha_from_evidence_lock>

# Restart BLUE stack
docker compose -f infrastructure/compose/compose.blue.yml pull
docker compose -f infrastructure/compose/compose.blue.yml up -d

# Verify kill-switch inactive after restart
curl -s http://127.0.0.1:8002/kill-switch
# Expected: "active": false
```

---

## 7. Related Documents

- `governance/p5_canary_readiness.yaml` — policy that requires this document
- `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md` — governance mapping (§9 references this pack)
- `docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md` — detailed kill-switch precheck procedure
- `docs/evidence/LR-040.md` — 72h soak gate (blocker)
- `docs/operations/72H_SOAK_TEST_RUNBOOK.md` — soak test procedure
