# Handoff: Aufgaben für nächste Session

**Erstellt**: 2025-12-31, 13:45 CET
**Von**: Claude (Session Lead: Issue #347 + #355 + #356 Analysis)
**Status Projekt**: Production-ready, 12/12 Services healthy, **BLOCKED by GitHub Billing**

---

## 📋 Kontext dieser Session

**Was wurde gemacht:**
- ✅ Issue #347: Dev vs Prod Logging Policy **MERGED** (PR #402)
- ✅ Issue #355: CI/CD Failure Analysis **COMPLETE** (Root Cause: Billing)
- ✅ Issue #356/PR #396: Contracts Review **CODE-COMPLETE** (19/19 tests passing)
- ✅ Dokumentation: `.orchestrator_issue_355_analysis.md`, `.orchestrator_pr_396_ready.md`

**Aktueller Stand:**
- **CRITICAL BLOCKER**: GitHub Billing/Spending Limit (Issue #400)
  - ALL 26 workflows failing with payment error
  - Blocks: Issue #355 (CI/CD), PR #396 (Contracts), Issues #354/#352/#349
- PR #396 is **ready to merge** - waiting only for billing fix
- Clear unblock path: Fix billing → Merge PR #396 → 3 green runs → P0 complete

**Commits dieser Session:**
- `950c7bd`: Issue #347 merged (logging policy)
- `4d53cb3`: Issue #355 analysis complete
- `b9e8757`: PR #396 readiness assessment

---

## 🔴 CRITICAL - User Action Required

### GitHub Billing/Spending Limit Fix (Issue #400)
**Priority**: P0 (BLOCKER - Alles wartet darauf!)
**Status**: External - User muss in GitHub Settings handeln

**Aktion für User**:
1. Gehe zu: https://github.com/settings/billing
2. Check "Spending limits" für Actions
3. Resolve payment issues oder increase limit
4. Verify: `gh run list --limit 5` zeigt keine billing errors mehr

**Warum kritisch:**
- Blockiert **alle** CI/CD Workflows (26 total)
- Blockiert PR #396 merge (contracts)
- Blockiert Issue #355 completion (CI/CD back to green)
- Blockiert Issue #354, #352, #349 (ebenfalls CI-abhängig)

**Sobald gefixt** → Nächster Agent kann direkt mit Merges weitermachen!

---

## 🤖 CLAUDE - Session Lead & Issue Orchestration

**Stärken**: Issue-Analyse, Systemcheck, Governance, Multi-Issue Coordination

### Aufgabe 1: Merge PR #396 (sobald Billing gefixt)
**Priority**: P0 (SOFORT nach Billing-Fix)
**Kontext**: PR #396 ist code-complete, alle Tests grün lokal
**Aktion**:
```bash
# 1. Verify CI is green
gh run list --limit 5 --json conclusion --jq '.[] | select(.conclusion=="success")'

# 2. Merge PR
gh pr merge 396 --squash --delete-branch

# 3. Verify contracts check appears in main
gh run list --branch main --limit 5
```

**Output**: Issue #356 ✅ COMPLETE

### Aufgabe 2: Achieve 3 Green Runs (Issue #355)
**Priority**: P0 (nach PR #396 Merge)
**Kontext**: Issue #355 fordert 3 consecutive green runs on main
**Aktion**:
1. Trigger workflow run (push oder manual dispatch)
2. Monitor: `gh run watch`
3. Verify required checks pass: unit, contracts, e2e_smoke
4. Repeat 2 more times (total: 3 green runs)

**Output**: Issue #355 ✅ COMPLETE

### Aufgabe 3: Continue P0 Queue (Issues #354, #352)
**Priority**: P0 (nach #355 complete)
**Kontext**: Weitere P0 Issues warten auf CI/CD
- #354: Deterministic E2E Test Path
- #352: Enable Alertmanager

**Aktion**: Checkout Issue branch, analyze, implement, test, PR

---

## 💼 COPILOT - Code Review & Testing

**Stärken**: Code-Review, Test-Writing, Refactoring, Best Practices

### Aufgabe 1: Service Migration for Contracts (Post-PR #396)
**Priority**: P1 (nach PR #396 Merge)
**Kontext**: PR #396 merged → Services müssen auf neue Contracts migrieren
**Betroffene Services**:
- `services/ws/service.py` - muss `trade_qty` statt `qty` publishen
- `services/signal/service.py` - muss `side` statt `direction` verwenden
- `services/risk/service.py` - muss backward compatibility für beide Felder haben

**Aktion**:
1. Review Migration Guide: `docs/contracts/MIGRATION.md`
2. Implement dual publishing (Phase 1: beide Felder publishen)
3. Add migration tests
4. Verify: Redis messages sind contract-konform

**Output**: 3 PRs (jeweils 1 Service) mit Migration Code + Tests

### Aufgabe 2: E2E Tests für Contract Validation
**Priority**: P1 (nach Service Migration)
**Kontext**: E2E Tests müssen neue Contracts validieren
**Aktion**:
- Update `tests/e2e/test_paper_trading_p0.py`
- Add contract validation: validate incoming Redis messages gegen JSON Schema
- Test dual publishing period (beide Felder vorhanden)

**Output**: Updated E2E tests + validation Report

---

## 🔧 CODEX - Automation & Tooling

**Stärken**: Script-Generierung, Automation, CI/CD Tools, Infrastructure

### Aufgabe 1: Contract Validation Tool
**Priority**: P2 (nach PR #396 Merge)
**Kontext**: Services brauchen Runtime-Validierung gegen Contracts
**Aktion**:
- Erstelle `tools/validate_redis_message.py`
- Input: Redis message (JSON), Schema path
- Output: Validation result + detailed errors
- Integration: Kann in Services als Middleware verwendet werden

**Output**: Validation Tool in `tools/` + Usage-Beispiele

### Aufgabe 2: CI/CD Health Check Script
**Priority**: P2 (für Monitoring)
**Kontext**: Wir wollen künftig früher sehen wenn CI/CD kaputt ist
**Aktion**:
```powershell
# Script: tools/check_ci_health.ps1
# Check: All workflows healthy? Any billing errors?
# Output: Report mit Status aller 26 Workflows
```

**Output**: CI Health Check Script in `tools/`

---

## 🔍 GEMINI - Research & Documentation

**Stärken**: Research, Analyse, Dokumentation, Architecture Documentation

### Aufgabe 1: Post-Mortem für Billing Issue
**Priority**: P3 (Documentation)
**Kontext**: Issue #400 war unerwarteter Blocker
**Aktion**:
- Dokumentiere: Wie kam es zum Billing-Problem?
- Root Cause: Scheduled workflows exhausted free tier?
- Lessons Learned: Früher erkennen? Monitoring?
- Prevention: Budget alerts, workflow optimization

**Output**: `docs/post-mortems/2025-12-31_billing_blocker.md`

### Aufgabe 2: Contract Migration Playbook
**Priority**: P2 (nach PR #396 Merge)
**Kontext**: Services müssen migriert werden - brauchen Anleitung
**Aktion**:
- Erstelle Step-by-Step Guide für Service-Migration
- Basiere auf: `docs/contracts/MIGRATION.md`
- Include: Code-Beispiele, Testing-Checkliste, Rollback-Plan

**Output**: `docs/playbooks/CONTRACT_MIGRATION_PLAYBOOK.md`

### Aufgabe 3: Architecture Update
**Priority**: P3 (Documentation)
**Kontext**: System ist gewachsen seit letztem Architecture Doc
**Aktion**:
- Update `ARCHITECTURE.md` mit aktuellen Services
- Add: Contract Flow Diagram (market_data → signal → execution)
- Add: Logging Policy (dev vs prod)

**Output**: Updated `ARCHITECTURE.md` + optional Diagrams

---

## 🎯 Gemeinsame Ziele

**Alle Agenten** sollten sich an diese Prinzipien halten:

1. **Billing-Check first**: Vor jeder CI-abhängigen Arbeit: `gh run list --limit 1` → Check for billing errors
2. **No forced merges**: PR reviews ernst nehmen, keine --force pushes auf main
3. **Tests required**: Jede Code-Änderung braucht Tests (unit + integration)
4. **Contract compliance**: Alle Redis messages müssen gegen Schemas validiert werden
5. **Clean commits**: Conventional Commits Format + Co-Authored-By Footer

**Referenzen**:
- `knowledge/CURRENT_STATUS.md` - Live System Status
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\agents\AGENTS.md` - Governance Rules
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\agents\CLAUDE.md` - Session Lead Role
- `.orchestrator_issue_355_analysis.md` - CI/CD Analysis
- `.orchestrator_pr_396_ready.md` - Contracts PR Status

---

## 📝 Session-Notes für nächsten CLAUDE Run

**Priority P0 (SOFORT - wartet auf User):**
- [ ] **User fixt GitHub Billing** (Issue #400) → Unblocks alles
- [ ] **Merge PR #396** (< 5 min nach Billing fix)
- [ ] **Achieve 3 green CI runs** (< 1 hour nach Merge)

**Priority P1 (danach):**
- [ ] Service Migration: cdb_ws, cdb_signal, cdb_risk (Contracts)
- [ ] Update E2E Tests für neue Contracts
- [ ] Issue #354: Deterministic E2E Test Path
- [ ] Issue #352: Enable Alertmanager

**Offene Fragen:**
- **Billing Fix Timeline?** User muss entscheiden wann das passiert
- **Service Migration Rollout?** Dual publishing 1 Woche oder 2?
- **E2E Tests blocking?** Müssen grün sein vor Service-Migration?

**Nächste Session sollte fokussieren auf:**
1. **Nach Billing Fix**: Schnell PR #396 mergen + Issue #355 complete
2. **Service Migration**: Alle 3 Services auf neue Contracts
3. **CI/CD Stabilität**: Monitoring etablieren (nie wieder Billing-Überraschung)

**Known Blockers:**
- 🔴 GitHub Billing (Issue #400) - **USER ACTION REQUIRED**
- 🟡 E2E Tests might need adjustments post-contracts (tbd)

**Quick Wins nach Billing Fix:**
- ✅ PR #396 merge (2 min)
- ✅ Issue #356 complete (immediate)
- ✅ Issue #355 complete (< 1h)
- ✅ 2 P0 Issues cleared in < 2 hours

---

## 📊 System Health Snapshot

**Docker Stack**: 12/12 Services healthy
**Git Status**: `main` @ `b9e8757` (clean)
**Worktrees**: 24 active (mostly stale, cleanup needed)
**Tests**: Unit tests passing (risk, signal expanded)
**CI/CD**: ❌ ALL failing (billing blocker)
**PRs Open**:
- #396 (Contracts) - ✅ CODE-COMPLETE, ready to merge
- #402 (Logging) - ✅ MERGED

**Priority Issues**:
1. #400 - Billing Fix (EXTERNAL)
2. #396 - Merge Contracts (READY)
3. #355 - CI/CD Green (READY after #396)
4. #354 - E2E Tests (NEXT)
5. #352 - Alertmanager (NEXT)

---

**Unblock-Path (Post-Billing Fix)**:
```
User fixt Billing (5 min)
  ↓
Merge PR #396 (2 min) → Issue #356 ✅
  ↓
3 Green Runs (30-60 min) → Issue #355 ✅
  ↓
Service Migration (2-4 hours)
  ↓
Issue #354, #352 (4-6 hours)
  ↓
ALL P0 ISSUES COMPLETE 🎉
```

**Total Time After Billing Fix**: ~8-12 hours to clear all P0s

---

**Ende Handoff - Viel Erfolg! 🚀**

**PS**: Billing fix ist der einzige Blocker. Alles andere ist ready to go! 💪
