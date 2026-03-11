---
role: governance
status: canonical
domain: completion_mechanism
type: policy
effective_date: 2026-02-06
source: LR-004
relations:
  implements: LR-004
  scope: all_lr_tasks
  enforcement: ci_fail_closed
---

# Deterministic Completion Governance (LR-004)

**Status**: Canonical
**Effective**: 2026-02-06
**Authority**: Live Readiness P0

## Zweck

Dieses Dokument definiert, wie Task-Completion in CDB funktioniert und warum dieser Mechanismus bindend ist.

## Grundprinzip

**Completion-Status ist manifest-getrieben** (`LR-TASKS.yaml`)

Jeder Task hat genau einen **terminalen STATE**:
- **DONE** — vollständig abgeschlossen, alle Akzeptanzkriterien erfüllt
- **BLOCKED** — gültig, aber explizit blockiert (mit Reason Code)

## Eigenschaften

1. **Kein impliziter Fortschritt**
   Status wird ausschließlich durch STATE-Dateien definiert, nicht durch GitHub Issues, Chat-Kontext oder "gefühlte" Fertigstellung.

2. **Kein Drift**
   Manifest (`LR-TASKS.yaml`) ist Single Source of Truth. Alle STATE-Dateien müssen mit Manifest übereinstimmen.

3. **Fail-Closed Validation**
   Status wird CI-seitig validiert. Ungültige Zustände blockieren Merge.

4. **BLOCKED ist gültig**
   BLOCKED ist ein terminaler, gültiger Zustand. Er darf CI nicht failen, muss aber explizit mit Reason Code dokumentiert sein.

## Validation Rules

Der Validator (`scripts/lr004_completion_guard.py`) prüft:
- **V000-V002**: Manifest-Integrität
- **V003-V005**: Cross-Validation (missing, orphan, duplicate STATE)
- **V006-V015**: STATE-Datei-Schema, Taxonomie, Evidence-Referenzen

Vollständige Spezifikation: `docs/live-readiness/LR-004-SPEC.md`

## Referenzen

### Spezifikation
- `docs/live-readiness/LR-004-SPEC.md` — vollständige Schema- und Rule-Definition

### Implementation
- `scripts/lr004_completion_guard.py` — Validator mit Rules V000-V015
- `docs/live-readiness/LR-TASKS.yaml` — Manifest (Single Source of Truth)

### Beispiele
- `docs/live-readiness/LR-004-STATE.yaml` — DONE-Beispiel
- `docs/live-readiness/LR-STATE-TEMPLATE.yaml` — Template für neue Tasks

## Akzeptanzkriterium

Jeder Agent / Maintainer versteht in **30 Sekunden**:
1. Status kommt aus Manifest + STATE-Dateien
2. Nur DONE oder BLOCKED sind gültig
3. CI validiert fail-closed
4. BLOCKED ist explizit, nicht implizit

## Enforcement

- **CI Job**: `lr-004-completion-guard` (runs after `contract-drift-guard`)
- **Exit Codes**: 0 = PASS, 1 = FAIL, 2 = CONFIG ERROR
- **Fail-Closed**: Jeder Validierungsfehler blockiert Merge

---

**Ende der Spezifikation**
