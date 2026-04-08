# Session Log: Issue #1301 — Context-Core/Bootstrap Canon Alignment

- Datum: 2026-03-28
- Branch: fix/1301-context-core-canon-alignment
- Commit: 1cc1ede
- PR: #1312
- Issue: #1301 (geschlossen)

## Ziel

Aktive Context-Core- und Bootstrap-Dokumente auf Working-Repo-Canon bringen.
Keine widersprüchlichen Aussagen zu SERVICE_CATALOG-Pfad oder Delivery-Gate-Schema mehr
in Dokumenten, die ein neuer Session-Start liest.

## Befund

- Bootstrap-Primärdocs (Root CLAUDE.md, agents/roles/CLAUDE.md, agents/AGENTS.md,
  knowledge/SYSTEM.CONTEXT.md): alle clean, keine falschen Pfade
- knowledge/GOVERNANCE_QUICKREF.md §2 verwies auf knowledge/governance/DELIVERY_APPROVED.yaml
  als kanonische Datei — der aktive Workflow delivery-gate.yml liest aber governance/DELIVERY_APPROVED.yaml
  (Root), nicht knowledge/governance/
- knowledge/context_build/CODEX_CONTEXT_CORE_VERIFICATION.md AUTHORITATIVE INPUTS enthielt
  drei nicht-existente Einträge und den falschen SERVICE_CATALOG-Pfad governance/SERVICE_CATALOG.md
- knowledge/operating_rules/ci_cd/TROUBLESHOOTING.md und CI_PIPELINE_GUIDE.md verwendeten
  bereits den korrekten Pfad governance/DELIVERY_APPROVED.yaml — kein Fix nötig

## Geänderte Dateien

- knowledge/GOVERNANCE_QUICKREF.md
- knowledge/context_build/CODEX_CONTEXT_CORE_VERIFICATION.md

## Durchgeführte Schritte

- GOVERNANCE_QUICKREF.md §2: Canonical file von knowledge/governance/DELIVERY_APPROVED.yaml
  auf governance/DELIVERY_APPROVED.yaml korrigiert; Hinweis auf nicht-CI-aktives Duplikat + #1311 ergänzt
- CODEX_CONTEXT_CORE_VERIFICATION.md AUTHORITATIVE INPUTS:
  - governance/SERVICE_CATALOG.md korrigiert auf knowledge/governance/SERVICE_CATALOG.md
  - docker-compose.base.yml entfernt (existiert nicht; infrastructure/compose/base.yml war bereits gelistet)
  - root stack_up.ps1 entfernt (existiert nicht im Repo-Root)
  - Header "Docs Repository (Context Core)" umbenannt auf "Context Core (Working Repo)"

## Out-of-Scope-Fund

- Zwei DELIVERY_APPROVED.yaml-Dateien mit unterschiedlichem Inhalt entdeckt:
  governance/DELIVERY_APPROVED.yaml (CI-aktiv) und knowledge/governance/DELIVERY_APPROVED.yaml (orphaned)
- Issue #1311 angelegt für Dual-File-Cleanup

## Ergebnis

- Eine belastbare Aussage zum Delivery-Gate-Pfad: governance/DELIVERY_APPROVED.yaml
- Eine belastbare Aussage zum SERVICE_CATALOG-Pfad: knowledge/governance/SERVICE_CATALOG.md
- Keine aktiven Bootstrap-Docs mit toten Input-Einträgen
- Kein Scope-Creep: LR-Status, Docs-Hub-Cleanup, Redis-Topologie nicht angefasst
- Issue #1301 geschlossen, PR #1312 offen
