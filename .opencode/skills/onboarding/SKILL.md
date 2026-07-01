<!--
Canonical Skill Source: docs/skills/onboarding/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: onboarding
description: >
  Canonical CDB onboarding slash command for agents, developers, and docs
  maintainers. Single smart read-only entrypoint: runs bootloader checks,
  scenario integrity, LR status, doctor/validator reachability. Produces a
  status card with two clear next paths. Read-only by default. No
  Live-Go, no Echtgeld-Go, no runtime/Docker/DB/MCP mutation. Safe for
  fresh clones and first-time agent sessions.
---

# /onboarding — Canonical CDB Onboarding Slash Skill

## Purpose

`/onboarding` is the **single smart developer entrypoint** for CDB onboarding.
It delegates to `tools/onboarding_orchestrator.py` which produces a read-only
status card with bootloader check, scenario integrity, LR status, doctor/validator
reachability, and two clear next paths.

If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, `mach onboarding`,
`fresh agent onboarding`, or equivalent, run: `python -m tools.onboarding_orchestrator`

If the user says `onboarding rehearsal`, `guided rehearsal`, `rehearsal mode`,
`generalprobe`, `tu so als waere ich neuer entwickler`, `reisefuehrer`,
`nicht staendig fragen`, `realitaetsnah simulieren`, `onboarding als test-szenario`,
or equivalent, run: `python -m tools.onboarding_simulation --mode guided-rehearsal --role developer`
Guided rehearsal ist kein Setup-GO und kein Live-Go. Mutierende Schritte werden nur simuliert.

**Nach guided-rehearsal-Lauf:** KEINE Anschlussfrage, keine Einladung, kein "Wenn du willst...".
Keine nummerierten Nachfolgemenues (1/2/3).
Der letzte Ausgabe-Absatz MUSS ein Abschluss sein: Status, ein naechster empfohlener Schritt, STOP.

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

Expected initial output - a status card with explicit state and allowed next actions:

```text
=== CDB Onboarding ===
Status: PASS | SETUP_WARN | BLOCKED
State: STATUS_ONLY | SETUP_CONFIRMATION_PENDING | SETUP_REQUIRED | DRY_RUN_COMPLETE | BLOCKED
check_scope: onboarding_status_default | onboarding_status_check_only
allowed_next_actions: <machine-readable list>
...
No changes made.
LR remains NO-GO.
trade-capable is not Live-Go.

Only when `State: SETUP_CONFIRMATION_PENDING`:

Moechtest du das Onboarding-Setup jetzt ausfuehren?

1. Ja
2. Abbruch
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
6. **Live Checks (evidence-pflichtig):** `git fetch`, `gh issue view`, `gh pr list`
   — Ergebnisse dokumentieren. Ohne diese Kommandos: "GitHub-/Check-Live nicht geprüft."
7. **Final Verdict:** `PASS` | `SETUP_WARN` | `BLOCKED`.

The orchestrator is **read-only by default**: no file writes, no report,
no setup mutation, no Docker, no secrets. Check-only is a dry-run only and
must not show or imply setup execution.

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

## Allowed Next Paths

Default output may expose these machine-readable next actions only:

- `status_only`
- `approve_setup`
- `request_setup_go`
- `abort`

The two-option prompt appears only when `State: SETUP_CONFIRMATION_PENDING`.
`1. Ja` maps only to setup approval / an allowed next action boundary in this
slice. It does not create `.env` or perform any local setup mutation.

## Agent Response Guardrails

### Response Contract (required fields)

- Report the orchestrator `Status`, `State`, warnings, and `allowed_next_actions`.
- Include `check_scope` and `skipped_checks` as part of the report.
- Include **Evidence-Abgrenzung**: was wurde geprüft, was nicht (siehe Wording Contract).
- Include **Safety-Grenzen**: LR NO-GO, kein Live-Go, kein Echtgeld-Go.

### Wording Contract (Evidence-Abgrenzung)

Trenne sauber zwischen geprüften und nicht geprüften Bereichen:

- **Ohne ausgeführte git/gh/check-Kommandos**:
  erlaubt → "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."
- **Mit Live-Kommandos**:
  erlaubt → "GitHub-/Repo-Live geprüft: <konkrete Kommandos und Ergebnis>."
- **`CURRENT_STATUS.md`** → "Engineering-Ledger, nicht Live-Wahrheit."
- **LR-SSOT** → "`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`"
- **trade-capable** → "Board-/Stage-Kontext, kein Live-Go."
- **Invarianten** → "Zentrale Sicherheitsgrenzen erkannt."

### Verbotene Phrasen

- "Live-Wahrheit geprüft: Ja" (nur mit konkreten git/gh/check-Kommandos erlaubt)
- "trade-capable ist deaktiviert" / "trade-capable ist aktiviert"
- "alle systemischen Invarianten erfasst" / "vollständige Live-Wahrheit geprüft"
- "CURRENT_STATUS.md ist Live-Wahrheit"
- "trade-capable erlaubt Live" / "trade-capable ist Live-Go"
- Freie Management-Zusammenfassung ohne Evidence-Abgrenzung

### Weitere Regeln

- Do not invent, renumber, or expand options beyond the orchestrator contract.
- Do not offer direct setup execution after `--mode check-only` / dry-run.
- If doctor output is partial, say so explicitly instead of presenting it as a full check.
- Board-Stage nie als Schalter oder Freigabe darstellen.
- Vollständigkeitsclaims nach Teilreads vermeiden.

All paths require explicit GO before execution. Default mode produces
no report and no setup mutation.

## External Documentation Lookup

When onboarding orientation mentions external tools or agent surfaces:
- Load `cdb-external-docs` for a complete list of external documentation references.
- Look up `docs/external-docs/index.md` for links to OpenCode, Cursor, Codex, Claude, Gemini docs.
- Relevant for new agents: Agent Surfaces section, GitHub Docs, MCP / Context docs.
- If internet is unavailable, reference local `docs/external-docs/index.md` and `AGENTS.md`.

## Agent Onboarding Readiness

Optional, informational readiness orientation for new agents and fresh clones.
Canonical description: [`../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md`](../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md).

- Four read-only checks: CLI compatibility scan, startup review, validation review, docs reliability review.
- Score is informational only: no CI gate, no merge gate, no automatic blocker. The primary output is a prioritized Top-fixes list.
- The external scanner `npx -y agent-compatibility@0.1.7 .` is optional and not bundled; missing Node/npm/network is `ENV_UNAVAILABLE` and must not be scored as a repo defect.
- Boundaries unchanged: LR remains NO-GO, `trade-capable` is not Live-Go, no Echtgeld-Go.

## Non-Goals

- No Live-Go.
- No Echtgeld-Go.
- No runtime, Docker, trading, strategy, LR, productive DB, SurrealDB, or MCP mutation.
- No automatic setup, report, or runtime action.
- No replacement of existing CDB subagents.
