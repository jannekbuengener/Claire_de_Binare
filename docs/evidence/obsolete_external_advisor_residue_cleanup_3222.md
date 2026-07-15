# Obsolete External Advisor Residue Cleanup — #3222

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
  - rg -n -i "Obsolete.*advisor|external.*advisor|decommissioned.*advisor" .
  - rg -n -i "Runtime.*advisor|Docker.*advisor|Infra.*advisor|Backfill.*advisor|Replay.*advisor" .
  - rg -n -i "advisor decommissioned" AGENTS.md agents docs knowledge README.md CURRENT_STATUS.md
  - git diff -- CURRENT_STATUS.md
  - gh issue view 3222 3221 3219 2985 1900 2977
  - gh pr list --state open
records_or_results:
  - HEAD == origin/main == c004473bb at branch start
  - Branch: docs/remove-obsolete-external-advisor-residues-3222
  - Active-policy obsolete advisor references found in: CURRENT_STATUS.md (lines 164-165)
  - All other obsolete advisor references: already correctly marked as historical/archive
  - #3221 body: already Jannek Human-GO aligned (fixed per #3221 cleanup)
  - #3221 stale preflight comment: already superseded by gate policy correction comment
repo_crosscheck:
  - CURRENT_STATUS.md:164-165 (before cleanup)
  - CURRENT_STATUS.md:164-165 (after cleanup)
  - All decision records with obsolete advisor references - already neutral/historical
  - All docs/evidence/reports/HISTORICAL_*.md files - already have historical banners
  - All docs/evidence/ files mentioning obsolete advisor - already marked historical
  - Archive files in docs/archive/ and knowledge/archive/ - explicitly archive
impact_on_plan:
  - CURRENT_STATUS.md: line 164 "Obsolete external advisor gate removed. Runtime/Docker/Infra: explicit Jannek Human-GO only."
  - CURRENT_STATUS.md: line 165 "Obsolete advisor-gate reference removed (#3222)."
  - No active-policy obsolete advisor residues remain in tracked, non-archive documentation
limitations:
  - Stale preflight comment on #3221 cannot be edited via gh cli; already superseded by gate policy correction comment
  - Archive files (docs/archive/, knowledge/archive/, knowledge/logs/sessions/) contain historical obsolete advisor references that are clearly labeled as archive/historical
  - docs/evidence/reports/HISTORICAL_*.md files are clearly labeled as orphaned/historical with banners
  - Decision records reference obsolete advisor as parenthetical historical notes
```

---

## 2. Bootloader-/Read-Order-Evidence

Canonical read order per `agents/AGENTS.md` § Read Order executed. LR NO-GO confirmed (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`). Board stage `trade-capable` confirmed orthogonal (`docs/runbooks/CONTROL_REGISTER.md`). `CURRENT_STATUS.md` treated as ledger.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch | `docs/remove-obsolete-external-advisor-residues-3222` |
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

### Obsolete advisor residues found and neutralized across tracked non-archive files.

All neutralized per: `Obsolete external advisor reference removed. Active gate: explicit Jannek Human-GO + repo evidence.`

---

## 6. Rewrite Policy

Applied: `Runtime/Docker/Backfill/Replay/Infra actions require explicit Jannek Human-GO.`
Neutralized: All obsolete external advisor references. Active gate: explicit Jannek Human-GO + repo evidence.

---

## 7. #3221 GitHub Cleanup

| Item | Status |
|---|---|
| #3221 body | Already Jannek Human-GO aligned (fixed in previous #3221 cleanup session) |
| #3221 comment 1 (preflight plan) | **Cannot edit via gh cli.** |
| #3221 comment 2 (gate policy correction) | Already posted: declares obsolete, active gate = Jannek Human-GO |
| #3221 comment 3 (follow-up) | Already posted: references #3222 cleanup |
| Superseded status: | Comment 1 is explicitly superseded by comment 2 (Gate Policy Correction). No further action needed. |

---

## 8. After Search Proof

All obsolete external advisor references removed or neutralized across tracked repo files.
Remaining matches (if any) are in explicitly labelled archive/historical directories and session logs.

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

No remaining unsafe references in active documentation. Historical archive files and session logs may contain obsolete references as part of their original context.

---

## 11. Status

`DONE_3222_MERGED`

All active obsolete external advisor references removed from tracked CDB documentation. Active runtime gate is unambiguous: `explicit Jannek Human-GO`. No Live-Go. LR remains NO-GO.
