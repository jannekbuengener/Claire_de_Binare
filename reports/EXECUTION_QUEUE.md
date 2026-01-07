# EXECUTION_QUEUE.md
**Generiert:** 2026-01-07
**Repo:** Claire_de Binare
**Ziel:** Now Queue - Produktion/CI/Security entblocken

---

## TOP10 PRs - Merge-Reihenfolge

### 1. PR #489 - hardening: enforce threshold contract (#487)
**Status:** MERGEABLE
**Labels:** none
**Warum:** Security-hardening, enforce threshold contract - direkt block-reduzierend für Produktion
**Risiko:** Niedrig - isolated contract enforcement
**Benötigte Checks:** CI grün, Code Review
**Merge-Methode:** `gh pr merge 489 --squash`
**Done:** PR merged, threshold contract enforced in runtime

---

### 2. PR #490 - Security: Prevent code injection in emoji-bot workflow
**Status:** MERGEABLE (Draft)
**Labels:** none
**Warum:** Code injection fix - security-hardening, reduziert Risiko
**Risiko:** Niedrig - isolierter Workflow fix
**Benötigte Checks:** CI grün, Security Review
**Merge-Methode:** `gh pr merge 490 --squash`
**Done:** PR merged, code injection risk eliminated

---

### 3. PR #491 - Fix incomplete URL substring sanitization
**Status:** MERGEABLE (Draft)
**Labels:** none
**Warum:** URL sanitization fix - security-hardening
**Risiko:** Niedrig - isolated fix in tests
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 491 --squash`
**Done:** PR merged, URL sanitization fixed

---

### 4. PR #496 - Potential fix for code scanning alert no. 1528
**Status:** MERGEABLE (Draft)
**Labels:** none
**Warum:** Code scanning alert fix - security compliance
**Risiko:** Niedrig - permissions fix
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 496 --squash`
**Done:** PR merged, code scanning alert 1528 resolved

---

### 5. PR #471 - Potential fix for code scanning alert no. 1511: Code injection
**Status:** MERGEABLE
**Labels:** none
**Warum:** Code injection fix - security-critical
**Risiko:** Niedrig-Mittel - code injection vulnerability
**Benötigte Checks:** CI grün, Security Review
**Merge-Methode:** `gh pr merge 471 --squash`
**Done:** PR merged, code injection vulnerability fixed

---

### 6. PR #508 - ci: fix ruff F841 in core/auth
**Status:** MERGEABLE
**Labels:** none
**Warum:** CI hygiene - linting fix, unblocks CI
**Risiko:** Niedrig - isolated linting fix
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 508 --squash`
**Done:** PR merged, ruff F841 fixed, CI green

---

### 7. PR #509 - chore(#470): remove .worktrees_backup from repo
**Status:** MERGEABLE
**Labels:** none
**Warum:** Repo hygiene - cleanup, unblocks CI (ruff/dependabot)
**Risiko:** Niedrig - cleanup only
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 509 --squash`
**Done:** PR merged, .worktrees_backup removed from repo

---

### 8. PR #480 - ci: fix docker context (refs #477)
**Status:** MERGEABLE
**Labels:** none
**Warum:** CI fix - docker context, unblocks CI jobs
**Risiko:** Niedrig - isolated docker fix
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 480 --squash`
**Done:** PR merged, docker context fixed

---

### 9. PR #479 - ci: register pytest markers (refs #477)
**Status:** MERGEABLE
**Labels:** none
**Warum:** CI fix - pytest markers, unblocks CI jobs
**Risiko:** Niedrig - isolated pytest fix
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 479 --squash`
**Done:** PR merged, pytest markers registered

---

### 10. PR #503 - test: scaffold pytest basics
**Status:** MERGEABLE
**Labels:** none
**Warum:** Test infrastructure - pytest basics, enables testing
**Risiko:** Niedrig-Mittel - adds test infrastructure
**Benötigte Checks:** CI grün
**Merge-Methode:** `gh pr merge 503 --squash`
**Done:** PR merged, pytest basics scaffolded

---

## TOP15 Issues - Reihenfolge, Abhängigkeiten, Done-Kriterien

### 1. Issue #501 - Repo scan: Branch protection, secrets path, test failures
**Labels:** priority:critical, agent:claude, agent:codex, agent:gemini
**Warum:** Repo hygiene - security/compliance baseline
**Abhängigkeiten:** Keine
**Done:** Branch protection enabled, secrets path verified, test failures documented

---

### 2. Issue #499 - Follow-up: Gordon Docker setup — Scout/Trivy/Metrics + Dockerfile strategy
**Labels:** prio:must, prio:should, type:security, scope:infra, docker, review, follow-up
**Warum:** Docker security - Gordon setup review, hardening
**Abhängigkeiten:** PR #497
**Done:** Scout/Trivy configured, Metrics setup, Dockerfile strategy documented

---

### 3. Issue #498 - Review: Gordon Docker setup + CI workflow claims
**Labels:** prio:must, prio:should, type:security, agent:gemini, agent:copilot
**Warum:** Docker review - CI workflow claims verification
**Abhängigkeiten:** PR #497, Issue #499
**Done:** Review complete, CI workflow claims verified/adjusted

---

### 4. Issue #492 - SCOPE - merge open branches to main (review)
**Labels:** prio:should, agent:claude, agent:gemini, agent:copilot
**Warum:** Branch cleanup - merge strategy, reduce chaos
**Abhängigkeiten:** Issue #501, TOP10 PRs
**Done:** Merge strategy defined, branches reviewed/merged/closed

---

### 5. Issue #477 - Follow-up: rerun status + blockers (refs #413 #26)
**Labels:** prio:must, status:idea, agent:codex, agent:copilot
**Warum:** CI rerun - blocker analysis, rerun strategy
**Abhängigkeiten:** PR #476, PR #504
**Done:** Rerun status documented, blockers identified/resolved

---

### 6. Issue #470 - [CLEANUP] Exclude .worktrees_backup from Dependabot + gitignore
**Labels:** prio:should, agent:copilot
**Warum:** Repo hygiene - exclude .worktrees_backup
**Abhängigkeiten:** PR #509
**Done:** .worktrees_backup excluded from Dependabot, added to .gitignore

---

### 7. Issue #467 - Follow up on Zero Restart automation
**Labels:** prio:must, scope:monitoring
**Warum:** Monitoring - zero restart automation
**Abhängigkeiten:** Issue #464, Issue #465, Issue #466
**Done:** Zero restart automation implemented, validated

---

### 8. Issue #464 - M1: Application Reject Circuit Breaker (Consecutive 4xx)
**Labels:** priority:P0, prio:should, prio:nice, type:risk_guard, area:ops, phase:build:3
**Warum:** Risk guard - circuit breaker, production safety
**Abhängigkeiten:** Issue #459
**Done:** Application reject circuit breaker implemented, tested

---

### 9. Issue #465 - M2: Kill-Switch Priority (Latency < 1s)
**Labels:** priority:P0, prio:should, prio:nice, type:risk_guard, area:ops, phase:build:3
**Warum:** Risk guard - kill-switch latency, production safety
**Abhängigkeiten:** Issue #459
**Done:** Kill-switch implemented, latency < 1s verified

---

### 10. Issue #466 - M3: Time Drift / NTP Guard
**Labels:** priority:P0, prio:should, prio:nice, type:risk_guard, area:ops
**Warum:** Risk guard - time drift, production safety
**Abhängigkeiten:** Issue #459
**Done:** Time drift / NTP guard implemented, validated

---

### 11. Issue #463 - GAP-006: Audit Trail & Hash-Chain Export
**Labels:** prio:must, priority:P0, type:gap, area:sec, agent:gemini
**Warum:** Audit trail - hash-chain export, compliance
**Abhängigkeiten:** Keine
**Done:** Audit trail implemented, hash-chain export verified

---

### 12. Issue #462 - GAP-005: Change Freeze Enforcement
**Labels:** prio:should, priority:P0, type:gap, area:gov, agent:gemini, phase:build:4
**Warum:** Governance - change freeze enforcement
**Abhängigkeiten:** Keine
**Done:** Change freeze enforcement implemented, validated

---

### 13. Issue #461 - GAP-004: Emergency Stop with Sub-30s SLA
**Labels:** prio:must, priority:P0, type:gap, area:eng, phase:build:3
**Warum:** Emergency stop - sub-30s SLA, production safety
**Abhängigkeiten:** Keine
**Done:** Emergency stop implemented, sub-30s SLA verified

---

### 14. Issue #460 - GAP-003: Safe Degradation & HALT Fallback
**Labels:** prio:should, priority:P0, type:gap, area:eng, phase:build:3
**Warum:** Risk guard - safe degradation, HALT fallback
**Abhängigkeiten:** Issue #459
**Done:** Safe degradation implemented, HALT fallback validated

---

### 15. Issue #459 - GAP-002: Defined DB/Redis Failure Modes
**Labels:** prio:must, priority:P0, type:gap, area:eng, phase:build:3
**Warum:** Failure modes - DB/Redis failure handling
**Abhängigkeiten:** Keine
**Done:** DB/Redis failure modes defined, tested

---

## Merge-Ready PRs (CI-Status-Check nötig)

**WICHTIG:** Branch `main` ist NICHT geschützt (Branch Protection 404).
- Keine "required" Checks definiert
- CI-Failures blockieren nicht automatisch mergen
- Manuelle Review-Disziplin ist essenziell

**Alle PRs sind MERGEABLE, aber haben CI-Probleme:**

- PR #489: Format Check (Black) fail, Linting (Ruff) fail, enforce-pr-template fail
- PR #509: Container Scan (Trivy) fail, ci fail, enforce-pr-template fail, validate-branch-name fail
- Andere PRs müssen noch geprüft werden

**Empfehlung:** CI-Probleme zuerst beheben, dann mergen.

**Wenn alle CI-Checks grün:**
```bash
for pr in 489 490 491 496 471 508 509 480 479 503; do
  gh pr merge $pr --squash --delete-branch
done
```

## Blocker PRs (Konflikt-auflösung nötig)

- PR #497 - CONFLICTING - Gordon Docker setup
- PR #504 - CONFLICTING - CI fetch fix
- PR #476 - CONFLICTING - CI path filters
- PR #481 - CONFLICTING - CI emoji report
- PR #478 - CONFLICTING - CI ruff exclude
- PR #422 - CONFLICTING - CI pin actions
- PR #420 - CONFLICTING - human made 2
- PR #394 - CONFLICTING - Alertmanager
- PR #300 - CONFLICTING - Smart PR auto-labeling
- PR #259 - CONFLICTING - Risk guards integration
- PR #239 - CONFLICTING - automatic PR labeling

## Nächste Schritte

1. Merge-ready PRs mergen (wenn CI grün)
2. Blocker PRs manuell reviewen und Konflikte auflösen
3. Issues nach TOP15 Reihenfolge bearbeiten
4. CI grün halten
