---
name: onboarding
description: >
  Canonical CDB onboarding entrypoint for Codex. Route slash and natural-language
  onboarding intent to the single smart read-only status-card path. Read-only by
  default. No Live-Go, no Echtgeld-Go, no runtime/Docker/DB/MCP mutation.
---

# CDB onboarding

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

Default output is the CDB Onboarding status card.

Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.

## External Documentation Lookup

When onboarding orientation mentions external tools or agent surfaces:
- Load `cdb-external-docs` for a complete list of external documentation references.
- Look up `docs/external-docs/index.md` for links to OpenCode, Cursor, Codex, Claude, Gemini docs.
- Relevant for new agents: Agent Surfaces section, GitHub Docs, MCP / Context docs.
- If internet is unavailable, reference local `docs/external-docs/index.md` and `AGENTS.md`.

## Run

```bash
python -m tools.onboarding_orchestrator
python -m tools.onboarding_orchestrator --format json
python -m tools.onboarding_orchestrator --mode check-only
```

## Guardrails

### Safety

- Read-only by default.
- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No file writes, no GitHub writes, no branch creation, no PR creation, no runtime/Docker/DB/MCP mutation, no secrets.

### Response Contract (required fields)

- Report only the orchestrator `Status`, `State`, warnings, and `allowed_next_actions`.
- Include `check_scope`, `skipped_checks`, and **Evidence-Abgrenzung** (was geprüft, was nicht).
- Include **Safety-Grenzen**: LR NO-GO, kein Live-Go, kein Echtgeld-Go.

### Wording Contract (Evidence-Abgrenzung)

- Ohne git/gh/check-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."
- Mit Live-Kommandos: "GitHub-/Repo-Live geprüft: <konkrete Kommandos und Ergebnis>."
- CURRENT_STATUS.md → Engineering-Ledger, nicht Live-Wahrheit.
- LR-SSOT → docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md.
- trade-capable → Board-/Stage-Kontext, kein Live-Go.

### Verbotene Phrasen

- "Live-Wahrheit geprüft: Ja" (nur mit konkreten Kommandos erlaubt)
- "trade-capable ist deaktiviert/aktiviert"
- "alle systemischen Invarianten erfasst"
- "CURRENT_STATUS.md ist Live-Wahrheit"
- "trade-capable erlaubt Live" / "ist Live-Go"
- Freie Management-Zusammenfassung ohne Evidence-Abgrenzung

### Weitere Regeln

- Do not invent extra onboarding options or reintroduce the removed legacy setup branch.
- `--mode check-only` is dry-run only and must not imply setup execution.
- The `1. Ja / 2. Abbruch` prompt is only valid when the orchestrator reports `State: SETUP_CONFIRMATION_PENDING`.
- Board-Stage nie als Schalter oder Freigabe darstellen.

## Agent Onboarding Readiness

Optional, informational readiness orientation for new agents and fresh clones.
Canonical description: [`../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md`](../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md).

- Four read-only checks: CLI compatibility scan, startup review, validation review, docs reliability review.
- Score is informational only: no CI gate, no merge gate, no automatic blocker. The primary output is a prioritized Top-fixes list.
- The external scanner `npx -y agent-compatibility@0.1.7 .` is optional and not bundled; missing Node/npm/network is `ENV_UNAVAILABLE` and must not be scored as a repo defect.
- Boundaries unchanged: LR remains NO-GO, `trade-capable` is not Live-Go, no Echtgeld-Go.
