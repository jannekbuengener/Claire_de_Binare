# Session Log — Session 22: Git-Divergenz + PR-Batch #1414/#1415 + Issue-Close

**Datum:** 2026-04-01
**Session:** 22

## Ausgangslage

- `main` lokal/remote divergiert: remote hatte `c6a51cda` (#1408), lokal lagen Sessions 18–21 noch nicht auf remote
- PR #1414 (eigentlicher #1412-Fix) war conflicting wegen pre-Rebase-Branch-Stand
- PR #1415 (Session-18–21-Batch) blockiert durch policy-gate (fehlende Kategorie)

## Durchgefuehrt

### Git-Divergenz auflösen
- Safety-Anchor `backup/pre-rebase-main` gesetzt
- `git fetch origin && git rebase origin/main` auf lokalem main
- Konflikt-Runde 1: 5 Dateien (CONTRIBUTING.md, governance/SECRETS_POLICY.md, knowledge/governance/SECRETS_POLICY.md, knowledge/governance/SECRET_ROTATION_POLICY.md, tools/secrets/README.md) — lokale Version (#1411) bevorzugt
- Konflikt-Runde 2: tools/test_pack/integrations/cdb-stack-adapter.ps1 — lokale Version (#1413-Legacy-Markierung) bevorzugt
- Rebase erfolgreich; c6a51cda in History integriert

### PR #1414 (#1412-Fix)
- Branch war pre-Rebase-Stand, enthielt alle Session-Commits → nicht direkt rebasebar
- Stattdessen: frischer Branch von origin/main + cherry-pick des eigentlichen #1412-Commits (7da0a253 → 18a0fab1)
- Force-push auf docs/issue-1412-lr-ssot-separation
- 9 Copilot-Review-Threads per GraphQL resolved
- Gemergt: bb0c42c0

### PR #1415 (Session-18–21-Batch)
- Nach #1414-Merge: Branch auf neues origin/main rebased (konfliktfrei)
- 30178d8c (Session-21-Close) behalten — bringt echten Inhalt (CURRENT_STATUS-History + Session-Log)
- policy-gate fail: cdb-stack-adapter.ps1 verhindert docs-only-Inference → manual-approval Label gesetzt
- 8 Copilot-Review-Threads per GraphQL resolved
- Gemergt: 04b91d4b

### Issues geschlossen
- #1410 ✓ — Runbooks/Playbooks BLUE+RED Canon
- #1411 ✓ — Secrets/Evidence SECRETS_PATH Canon
- #1412 ✓ — LR-AUDIT-STATUS / CURRENT_STATUS SSOT-Trennung
- #1413 ✓ — Discovery-Surface-Bereinigung

## Gelernt / Feedback gespeichert

- Session-Close-Commits bei Branch-Protection → Batch-PR statt Force-Push; Redundanz-Check nach abhängigen PRs
- Konflikte beim Rebase: immer erst prüfen ob Muster passt, nicht blind --theirs/--ours anwenden
- PR-Branch-Bereinigung: cherry-pick sauberer als kompletter Rebase wenn Branch viele irrelevante Commits trägt
