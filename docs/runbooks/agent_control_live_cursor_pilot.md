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

## Operator Bootstrap Preflight (before second Live-GO)

Do **not** start a second Cursor create until this checklist is green.
Read-only API checks alone are **not** sufficient after a terminal `ERROR`
with claimed-but-missing GitHub delivery.

### A) API-readable (agent may verify; no Create/Follow-up)

| Check | How | Pass criterion |
| --- | --- | --- |
| Credential presence | `CURSOR_API.txt` / `CURSOR_API_KEY` present | `credential_present=true` (never print value) |
| Auth identity | `GET /v1/me` | HTTP 200 |
| Models catalog | `GET /v1/models` | HTTP 200, ≥1 model |
| GitHub App repo scope | `GET /v1/repositories` (strict rate limit) | `https://github.com/jannekbuengener/Claire_de_Binare` listed |
| Prior run immutable | `GET /v1/agents/{id}` + `.../runs/{runId}` | Existing ERROR run readable; **no** new create |

### B) Dashboard-only (Jannek / operator; agent cannot complete)

Open [Cloud Agents → Environments](https://cursor.com/dashboard/cloud-agents#environments)
and the GitHub App installation for the Cursor account that owns the API key.

| Check | Pass criterion |
| --- | --- |
| GitHub connection | Cursor GitHub App installed for `jannekbuengener`; not only read-clone |
| Repository freigabe | `Claire_de_Binare` explicitly allowed for Cloud Agents |
| Push / PR permission | App can push branches **and** open PRs on this repo |
| Cloud Environment health | Environment for this repo shows last successful setup/snapshot (not failed install) |
| Resolution path | Confirm whether run uses repo `.cursor/environment.json` and/or a named saved environment |
| Expected delivery path | Decide: `autoCreatePR=true` + `startingRef=main` **or** work on an existing PR URL; document the expected branch/PR shape |
| Secrets / install | Any required install secrets present in dashboard (not in repo); install script expected to succeed |

### C) Repo-backed environment hint (evidence, not a green light)

- Repo has `.cursor/environment.json` (on `main`) with Dockerfile `../ci/Dockerfile` + pip install.
- Official resolution order: repo `environment.json` → personal saved env → team saved env.
- A broken Cloud Environment bootstrap can produce an opaque API `ERROR` with claimed `git.branches` and **no** GitHub object — treat dashboard Environment health as mandatory before the next Human-GO.

### D) Gate for exactly one second live create

Only after A+B are green, issue a **new** explicit Human-GO for **one** create.
Use a **new** state file / run id; keep the failed run
`run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b` as immutable evidence.
Still: no merge, no `cdb-local-ci`, Refs `#4258` only, issue stays open.

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
