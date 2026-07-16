# .github Control Plane

**Repo:** Claire de Binare  
**Stand:** 2026-07-16  
**Workflow-Bestand:** 57 YAML-Dateien plus `labels.json`  
**LR-Verdict:** NO-GO; Workflow-Hygiene ändert keine Live-Readiness.

## Zweck

`.github/` enthält CI, Security-Scans, Repository-Automation, Issue- und
PR-Vorlagen sowie die Control-Plane-Dokumentation. Der operative Bestand ist
vollständig im [Workflow-Register](../docs/runbooks/GITHUB_WORKFLOW_REGISTER.md)
erfasst.

## Ordner

| Pfad | Inhalt |
|---|---|
| `workflows/` | 57 aktive oder manuell nutzbare Workflows + `labels.json` |
| `scripts/` | Implementierungen für Control-, Hygiene- und Reporting-Workflows |
| `prompts/` | Gemeinsamer Control-Follow-up-Prompt |
| `control-plane/` | Manifeste, Validatoren und generierte Register |
| `ISSUE_TEMPLATE/` | Intake- und Governance-Vorlagen |
| `governance/` | Maschinenlesbare Freigabe- und Policy-Daten |

Die frühere Gemini-Command-Familie wurde zusammen mit ihren nicht erreichbaren
Workflows entfernt; `.github/commands/` ist keine aktive Workflow-Supportfläche
mehr.

## Kanonische Einstiege

- [Workflow-Register](../docs/runbooks/GITHUB_WORKFLOW_REGISTER.md)
- [Workflow-Runbook](../docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md)
- [Beziehungsgraph](../docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md)
- [CI-Index](../docs/ci/index.md)
- [Control Register](../docs/runbooks/CONTROL_REGISTER.md)

## Merge-Vertrag

Die merge-relevanten Check-Kontexte sind:

- `ci (Unit/Integration + Lint gesammelt)` aus `ci.yml`
- `policy-gate` aus `policy-gate.yml`

Workflow-Dateien ohne dokumentierten operativen Zweck werden nicht als
Deprecation-Stub aufbewahrt, sondern zusammen mit Tests und aktueller Doku
entfernt. Historische Evidence bleibt als Zeitzeugnis unverändert.

## Änderungspflichten

Bei Workflow-Änderungen sind im selben PR zu aktualisieren:

1. `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`
2. `.github/control-plane/generated/agent-workflow-map.json`
3. betroffene Runbooks, Diagramme und Contract-Tests
4. bei manifestierten Units die Dateien unter `control-plane/src/`

Für die Control-Plane gilt weiterhin: Änderungen an Automatisierung sind kein
LR-, Trading- oder Echtgeld-GO.
