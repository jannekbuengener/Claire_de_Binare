# Session 2026-07-12 — Binance E→D Relocation Phase 1 (#4004)

**Issue:** [#4004](https://github.com/jannekbuengener/Claire_de_Binare/issues/4004) (OPEN)  
**Branch:** `ops/binance-reloc-4004-e-to-d`  
**Worktree:** `D:\Dev\Workspaces\Repos\Claire_de_Binare__binance-reloc-4004`  
**Base SHA:** `b67d9ef960d55a1f492e666e630c382ddedc0b3a` (= `origin/main`)  
**Operator-GO:** `GO — BINANCE E→D MIGRATION PHASE 1` (2026-07-12)  
**Phase-1-Status:** `READY_FOR_SOURCE_DESTINATION_PREFLIGHT`

## Bootloader / Read Order

| Step | Pfad | Status |
|------|------|--------|
| Root pointer | `AGENTS.md` | gelesen |
| Agent registry + Read Order | `agents/AGENTS.md` | gelesen |
| Engineering status | `CURRENT_STATUS.md` | gelesen |
| LR verdict | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | gelesen (NO-GO) |
| Board stage | `docs/runbooks/CONTROL_REGISTER.md` | gelesen (`trade-capable`) |
| Session skill | `.cursor/skills/cdb-session-start/SKILL.md` | angewendet |

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: available
context_trust_level: none
records_found: none
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
tools_or_queries:
 - cdb_context_briefing (task_id=cdb-briefing-binance-reloc-phase1)
 - git fetch/status/rev-parse/worktree list
 - gh issue list (dedupe)
repo_crosscheck:
 - CURRENT_STATUS.md (#3990/PR #3997 DONE_MERGED)
 - agents/AGENTS.md Read Order
limitations:
 - Kein DB-backed Context; operative Wahrheit = GitHub + lokales FS (noch nicht in Phase 1 inventarisiert)
```

## GitHub Dedupe

- Suche: `Binance Backup E: D:`, `Binance-Historiendaten Backup 2`, `in:title Binance E: D:`
- Ergebnis: **0 offene Duplikate**
- Neues Issue angelegt: **#4004**

## Repo / Worktree Lage

| Surface | Branch | SHA | Working tree |
|---------|--------|-----|--------------|
| Main (`Claire_de_Binare`) | `main` | `b67d9ef9` | `?? tests/unit/market_data/test_binance_stress_rebuild.py` (unberührt) |
| Migration worktree | `ops/binance-reloc-4004-e-to-d` | `b67d9ef9` | clean |

## Phase 1 Grenzen (eingehalten)

- Keine Datenkopie, kein Hash, kein Manifest-Write, kein Junction-Cutover
- Keine Umbenennung/Löschung auf E:
- Keine Runtime/Docker/DB/MCP-Mutation

## Nächster Schritt

Phase 2: Source/Destination Preflight (read-only Inventar E:\CDB_artifacts\market_data, D: DevDrive/Space, Dry-run Evidence)

## Boundaries

- LR NO-GO; kein Live/Echtgeld
- Scope nur #3990 Binance-Korpus auf Backup II (E:)
