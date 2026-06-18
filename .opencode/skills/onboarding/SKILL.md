---
name: onboarding
description: >
  Canonical CDB onboarding slash command for agents, developers, and docs
  maintainers. Single smart read-only entrypoint: runs bootloader checks,
  scenario integrity, LR status, doctor/validator reachability. Produces a
  status card and numbered next-option hints. Read-only by default. No
  Live-Go, no Echtgeld-Go, no runtime/Docker/DB/MCP mutation. Safe for
  fresh clones and first-time agent sessions.
---

# /onboarding — Canonical CDB Onboarding Slash Skill

## Purpose

`/onboarding` is the **single smart developer entrypoint** for CDB onboarding.
It delegates to `tools/onboarding_orchestrator.py` which produces a read-only
status card with bootloader check, scenario integrity, LR status, doctor/validator
reachability, and numbered next-option hints.

If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, `mach onboarding`,
`fresh agent onboarding`, or equivalent, run: `python -m tools.onboarding_orchestrator`

Do not start `cdb-session-start` or `onboarding_doctor` as the primary path for onboarding intent.

**This is a session-skill / command-skill, not a subagent.**

## Default Invocation

```text
/onboarding
```

Equivalent default config:

```yaml
mode: default
writes: disabled
github_writes: disabled
lr: NO-GO
```

Expected initial output — a status card ending with numbered options:

```text
=== CDB Onboarding ===
Status: PASS | SETUP_WARN | BLOCKED
...
Keine Änderungen vorgenommen.
LR remains NO-GO.
trade-capable ist kein Live-Go.
Nächste Optionen:
  1. Setup-Plan anzeigen
  2. Setup vorbereiten
  3. Onboarding-Report schreiben
  4. Ersten sicheren Issue-Workflow simulieren
```

## Optional Forms

Optional aliases exist, but `/onboarding` remains canonical:

```text
/onboarding developer    # Developer onboarding path (alias)
/onboarding check        # Check-only mode
```

## Orchestrated Flow

1. **Bootloader check:** `AGENTS.md` + `agents/AGENTS.md` exist and are readable.
2. **Scenario integrity:** `ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md`
   exists and contains required governance terms.
3. **LR status:** `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` confirms NO-GO.
4. **Doctor / Validator reachability:** `tools/onboarding_doctor.py` and
   `tools.surrealdb.context_onboarding_doctor` respond.
5. **Env check:** `.env` presence is a setup-warn only (non-blocking).
6. **Final Verdict:** `PASS` | `SETUP_WARN` | `BLOCKED`.

The orchestrator is **read-only by default**: no file writes, no report,
no setup mutation, no Docker, no secrets. The output ends with numbered
next-option hints (no open yes/no question).

Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.

## Referenced V2 Surfaces

| Surface | Purpose |
|---------|---------|
| `AGENTS.md` | Root pointer -> canonical agent registry |
| `agents/AGENTS.md` | Read Order, Brain Evidence Gate, Context Brain Preflight Gate |
| `tools/onboarding_orchestrator.py` | **Single smart entrypoint** (status card + verdict) |
| `tools/onboarding_tour.py` | Role-specific read-only tour |
| `tools/onboarding_doctor.py` | Local developer setup preflight |
| `tools/validate_onboarding_docs.py` | Active onboarding docs integrity validator |
| `tools/onboarding_simulation.py` | Deterministic simulation runner |
| `docs/onboarding/first_issue_sandbox.md` | Guided first-issue rehearsal |
| `docs/onboarding/fresh_clone_rehearsal.md` | Read-only fresh-clone path |
| `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` | Visual onboarding map |
| `docs/onboarding/cdb_glossary.md` | CDB terminology reference |
| `DEVELOPER_ONBOARDING.md` | Developer setup and first PR workflow |

## Run the Orchestrator

```bash
# Default: status card
python -m tools.onboarding_orchestrator

# JSON output
python -m tools.onboarding_orchestrator --format json

# Check-only mode
python -m tools.onboarding_orchestrator --mode check-only

# PowerShell front door
.\tools\cdb.ps1 onboarding
```

## Safety Boundaries

- **LR remains NO-GO** — SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board stage `trade-capable` is not Live-Go**
- **No Echtgeld-Go**
- **Read-only by default** — no file writes, no GitHub writes, no branch creation,
  no PR creation, no runtime/Docker/DB/MCP mutation, no secrets.
- **No subagent replacement** — `/onboarding` is a slash-skill, not a subagent.
  CDB subagents (`/cdb-governance-gatekeeper`, etc.) remain unchanged.

## BLOCKER Conditions

The flow produces `BLOCKED` if:

- Bootloader files (`AGENTS.md`, `agents/AGENTS.md`) are missing or unreadable
- Scenario document `ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md`
  is missing or unreadable

Non-blocking warnings (`SETUP_WARN`):

- `.env` fehlt (setup warn, kein blocker)
- Context Doctor nicht initialisiert (setup warn, kein blocker)
- `onboarding_doctor` nicht erreichbar

## Allowed Next Options (numbered, no open question)

```text
1. Setup-Plan anzeigen
2. Setup vorbereiten
3. Onboarding-Report schreiben
4. Ersten sicheren Issue-Workflow simulieren
```

All four options require explicit GO before execution. Default mode produces
no report and no setup mutation.

## Non-Goals

- No Live-Go.
- No Echtgeld-Go.
- No runtime, Docker, trading, strategy, LR, productive DB, SurrealDB, or MCP mutation.
- No automatic setup, report, or runtime action.
- No replacement of existing CDB subagents.
- No open yes/no question in default output.
