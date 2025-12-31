# GOVERNANCE AUDITOR - BRIEFING

**Mission:** Reduziere Governance-Drift durch Tests-as-Governance

**Kontext:**
- CDB hat 60-70% Drift (siehe governance-drift-audit.md)
- Freqtrade hat nur 5-10% Drift WEGEN Tests-as-Governance
- Problem: "Over-governed, under-enforced"

**DEINE AUFGABE:**

## 1. Tests-as-Governance Strategie
**FREQTRADE PATTERN:**
```yaml
# CI Gate
pytest --cov=freqtrade --cov-fail-under=75
# ← Coverage-Drop = Red CI = Merge verhindert
```

**CDB ADAPTATION:**
```yaml
# Unit Tests
pytest tests/unit --cov=core --cov=services --cov-fail-under=70

# Contract Tests
pytest tests/contracts -v --tb=short
# ← Schema-Verstöße = Red CI

# Governance Guardrails
pytest tests/governance/test_determinism_guardrails.py
# ← time.time() usage = Red CI
```

## 2. Enforcement Mechanisms
**WAS muss TECHNISCH ERZWUNGEN werden?**

**SOFORT (Branch Protection):**
- Direct Commits auf main → VERBOTEN (GitHub API)
- Required Reviews → ERZWUNGEN (CODEOWNERS)
- Required Status Checks → CI muss grün sein

**DIESE WOCHE (CI/CD Gates):**
- Coverage-Gate (70%+)
- Contract Tests als Gate
- Determinism Guardrails als Gate

**NÄCHSTEN MONAT (Pre-Commit Hooks):**
```yaml
# .pre-commit-config.yaml
- id: determinism-guard
  entry: pytest tests/governance/test_determinism_guardrails.py
  # ← time.time() usage = Commit verhindert

- id: contract-validation
  entry: pytest tests/contracts -v
  # ← Schema-Verstöße = Commit verhindert
```

## 3. Drift-Reduktion Roadmap
**VON:** "Governance als Dokumentation"
**ZU:** "Governance as Code"

**MESSBAR:**
```
Woche 1: 60-70% Drift
  → Branch Protection aktiviert
Woche 2: 50-60% Drift
  → CI/CD grün + Coverage-Gate
Woche 4: 40-50% Drift
  → Contract Tests als Gate
Monat 2: 20-30% Drift
  → Pre-Commit Hooks aktiv
```

## 4. Deliverable
**FORMAT:**
```markdown
## TESTS-AS-GOVERNANCE STRATEGIE:
[Wie Tests Governance erzwingen]

## ENFORCEMENT ROADMAP:
**Woche 1: SOFORT**
- [ ] Branch Protection aktivieren
- [ ] Required Status Checks definieren

**Woche 2-4: HOCH**
- [ ] CI/CD back to green (Issue #355)
- [ ] Coverage-Gate (70%+)
- [ ] Contract Tests als Gate

**Monat 1-2: MITTEL**
- [ ] Pre-Commit Hooks
- [ ] Determinism Guardrails
- [ ] E2E Tests als Gate

## DRIFT-REDUKTION:
[Messbarer Plan: 60% → 20%]
```

**ZEIT:** 30 Minuten
**OUTPUT:** D:\Dev\Workspaces\Repos\Claire_de_Binare\.orchestrator_outputs\governance_enforcement_plan.md
