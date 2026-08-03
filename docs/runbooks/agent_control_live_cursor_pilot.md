# Agent Control — Live Cursor Pilot (Zero-Click)

Status: Operator runbook  
Scope: Issue `#4258` live Cursor cloud pilot (Human-GO)  
Refs: `#4258` only — never Closes, never merge, never `cdb-local-ci` publish

## Boundaries

- Default pilot remains **mock** (`--provider mock`).
- Live path requires **explicit Human-GO**: `--provider cursor-cloud-api --human-go-live-cursor`.
- Credential bootstrap is **MANUAL_BOOTSTRAP_ONLY**: operator places `CURSOR_API_KEY` in the
  local secrets directory or environment. Agents must not invent or print secret values.
- Cursor Approval Agents remain **MANUAL_BOOTSTRAP_ONLY** — pilot pauses at
  `AWAITING_APPROVAL` and does not auto-merge.
- LR stays NO-GO. No live trading, no productive DB/MCP mutation, no BLUE/RED runtime change.

## Registry surfaces

| Item | Id |
| --- | --- |
| Agent | `acp-live-cursor-pilot` |
| Provider profile | `cursor-cloud-api.v1` (`live_dispatch: false`) |
| Environment profile | `cursor-live-pilot.v1` (`runtime_class: mock` for CI doctor; live only via Human-GO flags) |

## Operator Bootstrap Preflight (dashboardless)

Manuelle Cursor-Dashboard-Klickpfade sind **kein** normaler Operator-Schritt.
Voraussetzungen werden programmgesteuert geprüft:

```bash
# Optional: load CURSOR_API_KEY from secrets file into the shell env first
python -m tools.agent_control pilot cursor-preflight \
  --repository jannekbuengener/Claire_de_Binare \
  --environment jannekbuengener/Claire_de_Binare \
  --binding-mode repos_plus_repo_config \
  --state artifacts/agent_control/live-pilot-runstore.json \
  --out artifacts/agent_control/cursor-live-preflight.json
```

### Dual-run ERROR support bundle (read-only)

When existing Cursor runs terminate `ERROR` without a structured error object,
build a redacted dual-run support package from recorded states (zero POSTs,
no new agents/runs):

```bash
python -m tools.agent_control pilot cursor-support-bundle \
  --state-run1 tests/fixtures/agent_control/cursor/dual_run_error_run1.json \
  --state-run2 tests/fixtures/agent_control/cursor/dual_run_error_run2.json \
  --shared tests/fixtures/agent_control/cursor/dual_run_shared_meta.json \
  --output artifacts/agent_control/dual_run_4258_support \
  --tracked-summary docs/evidence/agent_control/CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md
```

Documented usage/artifacts paths are agent-scoped (`GET /v1/agents/{id}/usage`,
`GET /v1/agents/{id}/artifacts`). A 404 on run-scoped `/runs/{runId}/usage` is
not evidence that usage is missing. Support drafts are ready-to-send but must
not be mailed without a new explicit operator authorization.

Canonical create binding for CDB: **`repos` + versioned `.cursor/environment.json`**
(`--binding-mode repos_plus_repo_config`). Official API treats named `env` and
`repos` as mutually exclusive. Named dashboard environments cannot be listed or
ID-bound via public OpenAPI (`PUBLIC_API_GAP_*`).

The preflight report schema is `cdb.cursor_live_preflight.v1`.
`ready_for_live_run=true` only when all fail-closed gates pass (including a
**readable** GitHub App installation with `contents=write` and
`pull_requests=write`). User `gh` tokens often cannot read another App's
installation — that is recorded as `PUBLIC_API_GAP_GITHUB_INSTALLATION_READ`,
not as a fake PASS.

### Public surfaces used

| Surface | Role |
| --- | --- |
| `GET /v1/me`, `/v1/models`, `/v1/repositories` | Cursor account + repo visibility |
| `GET /v1/agents/{id}` (+ run) | Immutable prior-run evidence; resolved `env` if present |
| `.cursor/environment.json` + `ci/Dockerfile` | Repo configuration as code |
| `gh api repos/...`, branch protection, `apps/cursor` | GitHub metadata (read-only) |
| `GET /repos/.../installation` | Installation permissions when token allows |

### Explicit non-goals

- No private `cursor.com` dashboard API
- No browser automation
- No new Cursor agent/run from preflight
- No merge / `cdb-local-ci` / issue close

## Credential bootstrap (MANUAL_BOOTSTRAP_ONLY)

1. Obtain a Cursor API key outside the agent session.
2. Export `CURSOR_API_KEY` in the operator shell **or** place a non-empty file
   `CURSOR_API_KEY` / `CURSOR_API_KEY.txt` under the operator secrets directory.
3. Never paste the key into issues, PRs, chat, or pilot reports.
4. Presence is checked fail-closed (`PRECONDITION_BLOCKED`) before any network call.

## Zero-Click operator flow

```bash
# 1) Validate registry (includes live-pilot env + agent)
python -m tools.agent_control registry validate --config config/agent-control

# 2) Optional doctor on the live-pilot env (offline / mock runtime_class)
python -m tools.agent_control environment doctor \
  --profile cursor-live-pilot.v1 \
  --config config/agent-control \
  --offline

# 3) Human-GO live pilot (operator shell with CURSOR_API_KEY present)
python -m tools.agent_control pilot run \
  --manifest <LIVE_MANIFEST.json> \
  --provider cursor-cloud-api \
  --human-go-live-cursor \
  --state artifacts/agent_control/live-pilot-runstore.json \
  --out artifacts/agent_control/live-pilot-report.json

# Optional: request Cursor autoCreatePR (still Human-GO gated; no merge)
#   --auto-create-pr

# 4) Resume after process restart (same state file; reuses provider_run_id)
python -m tools.agent_control pilot run \
  --manifest <LIVE_MANIFEST.json> \
  --provider cursor-cloud-api \
  --human-go-live-cursor \
  --state artifacts/agent_control/live-pilot-runstore.json \
  --resume <RUN_ID> \
  --out artifacts/agent_control/live-pilot-report.json
```

Fail-closed without Human-GO:

```bash
python -m tools.agent_control pilot run \
  --manifest <LIVE_MANIFEST.json> \
  --provider cursor-cloud-api
# → PILOT_HUMAN_GO_REQUIRED
```

## Expected terminal shape

1. Credential presence → PASS (or `PRECONDITION_BLOCKED` with zero network).
2. Dispatch via `cursor-cloud-api` with injected/live HTTP under Human-GO.
3. GitHub delivery verify (`gh`) binds head SHA + changed-file allowlist.
4. Watch with `auto_advance_success=False` → **`AWAITING_APPROVAL`**.
5. Run evidence may be HOLD (non-terminal) — acceptable.
6. Approval context recommendation is advisory only; authority limits stay all-false.
7. Report limitations include `live_cursor_pilot`,
   `awaiting_approval_operator_handoff`,
   `cursor_approval_agents_manual_bootstrap_only`.

## Non-goals

- No squash merge, no `--admin`, no branch-protection mutation.
- No `cdb-local-ci` publish from this pilot.
- No issue close for `#4258` (Refs only).
- No real Cursor agents from unit tests (fake HTTP / fake `gh` only).
