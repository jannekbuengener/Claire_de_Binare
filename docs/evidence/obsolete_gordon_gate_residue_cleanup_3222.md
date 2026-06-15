# Obsolete Gordon Gate Residue Cleanup — #3222

Status Class: Scoped evidence / governance cleanup result
Issue: #3222
Parent: #1900
Control Refs: #2985, #3221, #2977
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - rg -n -i "\bGordon\b|GordonGate|Gordon-Gate|Gordon gate|Gordon approval|Gordon-GO|ask Gordon|consult Gordon" . --type-not py --type-not yaml --type-not json
  - rg -n -i "Runtime.*Gordon|Docker.*Gordon|Infra.*Gordon|Backfill.*Gordon|Replay.*Gordon" .
  - rg -n -i "Gordon" AGENTS.md agents docs knowledge README.md CURRENT_STATUS.md PROJECT_STATUS.md CONTRIBUTING.md DEVELOPER_ONBOARDING.md
  - git diff -- CURRENT_STATUS.md
  - gh issue view 3222 3221 3219 2985 1900 2977
  - gh pr list --state open
records_or_results:
  - HEAD == origin/main == c004473bb at branch start
  - Branch: docs/remove-obsolete-gordon-gate-residues-3222
  - 67+ files in repo contain the word "Gordon" (including archives, session logs, evidence, decision records)
  - Active-policy Gordon references found in: CURRENT_STATUS.md (lines 164-165)
  - All other Gordon references: already correctly marked as historical/decommissioned/archive
  - #3221 body: already Jannek Human-GO aligned (fixed per #3221 cleanup)
  - #3221 stale preflight comment: already superseded by gate policy correction comment
repo_crosscheck:
  - CURRENT_STATUS.md:164-165 (before cleanup)
  - CURRENT_STATUS.md:164-165 (after cleanup)
  - All decision records with "(Gordon gate decommissioned)" - already neutral/historical
  - All reports/GORDON_*.md files - already have historical banners
  - All docs/evidence/ files mentioning Gordon - already marked historical
  - Archive files in docs/archive/ and knowledge/archive/ - explicitly archive
impact_on_plan:
  - CURRENT_STATUS.md: line 164 "Gordon: `GORDON_NOT_AVAILABLE`" → "Obsolete external advisor gate removed. Runtime/Docker/Infra: explicit Jannek Human-GO only."
  - CURRENT_STATUS.md: line 165 "Gordon-Decommission als separates Follow-up #2689" → "Obsolete advisor-gate reference removed (#3222)."
  - No active-policy Gordon gate residues remain in tracked, non-archive documentation
limitations:
  - Stale preflight comment on #3221 cannot be edited via gh cli; already superseded by gate policy correction comment
  - Archive files (docs/archive/, knowledge/archive/, knowledge/logs/sessions/) contain historical Gordon references that are clearly labeled as archive/historical
  - reports/GORDON_*.md files are clearly labeled as orphaned/historical with banners
  - Decision records reference "Gordon gate decommissioned" as parenthetical historical notes — acceptable
```

---

## 2. Bootloader-/Read-Order-Evidence

Canonical read order per `agents/AGENTS.md` § Read Order executed. LR NO-GO confirmed (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`). Board stage `trade-capable` confirmed orthogonal (`docs/runbooks/CONTROL_REGISTER.md`). `CURRENT_STATUS.md` treated as ledger.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch | `docs/remove-obsolete-gordon-gate-residues-3222` |
| HEAD at branch start | c004473bb |
| origin/main | c004473bb (equal) |
| Worktree | clean (2 pre-existing untracked dirs) |
| #3222 | OPEN, execution in progress |
| #3221 | OPEN, body Jannek Human-GO aligned |
| #3219 | CLOSED |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN |
| Open PRs | Dependabot-only (4) |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

---

## 4. Before Search Results

### Active-policy Gordon residues found in tracked non-archive files:

| File | Line | Content | Action |
|---|---|---|---|
| `CURRENT_STATUS.md` | 164 | `Gordon: \`GORDON_NOT_AVAILABLE\`` | Rewritten — reads as if Gordon is an expected gate |
| `CURRENT_STATUS.md` | 165 | `Gordon-Decommission als separates Follow-up #2689 angelegt; keine Gordon-Bereinigung in diesem Scope.` | Rewritten — references decommission as open follow-up |

### All other Gordon references in active docs — already correctly handled:

| Category | Status |
|---|---|
| `reports/GORDON_*.md` | Already banner: "Not an active operational gate" / "Orphaned / historisch" |
| `reports/EXECUTION_QUEUE.md` | Already banner: historical |
| `reports/BLUE_RED_IMPLEMENTATION_SUMMARY.md` | Already banner: decommissioned |
| `docs/evidence/mexc_same_venue_data_quality_policy_3091.md` | Already: "historical/decommissioned" |
| `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_*.md` | Already: "historical / decommissioned" |
| `knowledge/decisions/CDB_CONTEXT_MANAGED_*.md` | Already: "(Gordon gate decommissioned)" as historical parenthetical |
| `knowledge/CDB_KNOWLEDGE_HUB.md` | Already: "(Gordon — historisch/decommissioned; siehe #2689)" |
| `knowledge/deep-issues-lab/010 Sichere Architektur für den Gordon-Agenten.md` | Already: "historical concept" banner |
| `knowledge/deep-issues-lab/cdb_ws.md` | Already: "kein Gordon/Docker-AI operatives Gate (#2689)" |
| `services/execution/EXECUTION_SERVICE_STATUS.md` | Already: historical/decommissioned banner |
| `infrastructure/database/migrations/*.sql` | Already: "Gordon gate decommissioned" historical notes |
| `docs/surrealdb/*.md` | Already: historical references |
| `docs/archive/` | Explicit archive directory |
| `knowledge/archive/` | Explicit archive directory |
| `knowledge/logs/sessions/` | Session logs — historical by nature |

---

## 5. Files Changed

| File | Change | Rationale |
|---|---|---|
| `CURRENT_STATUS.md:164` | `Gordon: \`GORDON_NOT_AVAILABLE\`` → `Obsolete external advisor gate removed. Runtime/Docker/Infra: explicit Jannek Human-GO only.` | Active ledger line read as if Gordon is an expected but unavailable gate |
| `CURRENT_STATUS.md:165` | `Gordon-Decommission als separates Follow-up #2689 angelegt; keine Gordon-Bereinigung in diesem Scope.` → `Obsolete advisor-gate reference removed (#3222). Runtime/Docker/Infra: explicit Jannek Human-GO only.` | Decommission follow-up is now resolved by #3222; active policy clarified |

---

## 6. Rewrite Policy

Applied: `Runtime/Docker/Backfill/Replay/Infra actions require explicit Jannek Human-GO.`

Removed:
- Gordon as required advisor/gatekeeper (`CURRENT_STATUS.md` ledgers)
- Gordon gate status lines (`GORDON_NOT_AVAILABLE` removed)
- Decommission follow-up language (superseded by #3222 completion)

Historical ledger entries neutralized with `Obsolete external advisor gate removed` / `Obsolete advisor-gate reference removed (#3222)` — these preserve the chronological context without creating active-policy confusion.

---

## 7. #3221 GitHub Cleanup

| Item | Status |
|---|---|
| #3221 body | Already Jannek Human-GO aligned (fixed in previous #3221 cleanup session) |
| #3221 comment 1 (preflight plan) | **Cannot edit via gh cli.** Contains `PLAN_READY_FOR_GORDON_AND_JANNEK_RUNTIME_GO` and `Gordon-Frage` section |
| #3221 comment 2 (gate policy correction) | Already posted: declares Gordon obsolete, active gate = Jannek Human-GO |
| #3221 comment 3 (follow-up) | Already posted: references #3222 cleanup |
| Superseded status: | Comment 1 is explicitly superseded by comment 2 (Gate Policy Correction). No further action needed. |

---

## 8. After Search Proof

```bash
rg -n -i "\bGordon\b|GordonGate|Gordon-Gate|Gordon gate|Gordon approval|Gordon-GO|ask Gordon|consult Gordon" AGENTS.md agents docs knowledge README.md CURRENT_STATUS.md PROJECT_STATUS.md CONTRIBUTING.md DEVELOPER_ONBOARDING.md || true
```

**Result: No active-policy Gordon gate residues** in tracked non-archive active documentation.

Remaining Gordon mentions (all correctly labeled with historical/decommissioned/disclaimer banners):

| Location | Classification | Justification |
|---|---|---|
| `reports/GORDON_*.md` (3 files) | Archive/historical | Banner: "Not an active operational gate" |
| `reports/EXECUTION_QUEUE.md` | Historical | Banner: historical context |
| `reports/BLUE_RED_IMPLEMENTATION_SUMMARY.md` | Historical | Banner: decommissioned |
| `knowledge/decisions/CDB_CONTEXT_MANAGED_*.md` | Historical parenthetical | "(Gordon gate decommissioned)" — explains policy evolution |
| `knowledge/CDB_KNOWLEDGE_HUB.md` | Historical reference | "(Gordon — historisch/decommissioned)" |
| `knowledge/deep-issues-lab/010 Sichere Architektur für den Gordon-Agenten.md` | Archive/historical | Banner: "historical concept" |
| `docs/evidence/*.md` | Historical reference | Already marked "historical/decommissioned" |
| `docs/surrealdb/*.md` | Historical reference | Audit findings, not active policy |
| `infrastructure/database/migrations/*.sql` | Historical notes | "Gordon gate decommissioned" in header comments |
| `docs/archive/`, `knowledge/archive/` | Explicit archive | Archive directory |
| `knowledge/logs/sessions/` | Session logs | Historical by nature |

---

## 9. Safety Boundaries

| Rule | Status |
|---|---|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced |
| No Runtime/Docker/Compose | Enforced |
| No DB mutation | Enforced |
| No workflow_dispatch | Enforced |
| No secrets exposed | Enforced |
| No Product-Complete claim | Enforced |
| No Candidate #4 / PB1 / RMR / Momentum rescue | Enforced |
| Board stage `trade-capable` is not Live-Go | Enforced |

---

## 10. Restunsicherheiten

1. Stale #3221 preflight comment (IC_kwDOQUkXUM8AAAABGOHazQ) still contains Gordon gate language and `PLAN_READY_FOR_GORDON_AND_JANNEK_RUNTIME_GO` status. Cannot be edited via gh cli. Gate Policy Correction comment (#2) explicitly supersedes it.
2. `docs/archive/docs_hub_snapshot/agents/AGENTS.md` still contains "Ask Gordon" Docker AI tool context — this is in an explicitly labelled archive directory and is not active policy.
3. `knowledge/archive/` files contain historical Gordon references — clearly labelled as archive.
4. `reports/GORDON_*.md` files remain in the repo as historical artifacts with clear "not active" banners. These do not create active-policy confusion.
5. Decision records using "(Gordon gate decommissioned)" as parenthetical notes are acceptable — they document policy evolution without creating active gating.

---

## 11. Status

`DONE_3222_MERGED`

All active Gordon/GordonGate references removed from tracked CDB documentation. Active runtime gate is unambiguous: `explicit Jannek Human-GO`. No Live-Go. LR remains NO-GO.
