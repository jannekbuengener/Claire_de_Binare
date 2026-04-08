# AGENTS

Status: Canonical
Scope: Working Repo

Diese Datei ist die kanonische Agenten-Registry fuer das Working Repo `Claire_de_Binare`.
Sie ersetzt die alte Split-Repo-Annahme, nach der Agenten- und Governance-Doku standardmaessig
in einem separaten externen Doku-Repo gesucht wurde.

## Read Order

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`

## Canonical Domains

- `agents/`
  - Gemeinsame Agenten-Entrypoints und lokale Agenten-Navigation.
- `knowledge/governance/`
  - Kanonische Governance-, Policy- und Invariant-Dokumente.
- `knowledge/`
  - Kanonische Knowledge-Hub- und Decision-Hub-Dokumente.
- `.github/`
  - GitHub-Community-, Template- und Maintainer-Artefakte.
- `docs/`
  - Navigation, Runbooks, Archive und abgeleitete Views.

## Status Surfaces

- `CURRENT_STATUS.md`
  - Autoritative Quelle fuer aktuellen Repo-, Main-, Test- und Arbeitsstatus.
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - Autoritative Quelle fuer operativen Go/No-Go-Status und Echtgeld-Blocker.
- `docs/runbooks/CONTROL_REGISTER.md`
  - Autoritative Quelle fuer aktuellen Board-/Stage-Status und operativen Fokus im Control Board.
- `PROJECT_STATUS.md`, `knowledge/CURRENT_STATUS.md`
  - Historische Snapshots; keine aktuelle repo-weite oder operative Wahrheit.

## Current Project Reality

- Working Repo bleibt der produktive Canon fuer Agenten-, Governance-, Knowledge- und Navigationsdoku.
- Aktuelle Board-Stage ist `trade-capable` (ratifiziert 2026-04-08 via Issue `#1492`).
- Diese Board-Stage ist orthogonal zum LR-System; `LR-050` bleibt `NO-GO` und autorisiert kein Live-Kapital.

## Operating Rules

- `AGENTS.md` im Repo-Root ist nur ein Pointer auf diese Datei.
- Agenten und Tools sollen standardmaessig lokale Pfade im Working Repo verwenden.
- Stage-/Board-Aussagen und LR-Go/No-Go-Aussagen muessen strikt getrennt bleiben.
- Eine Board-Stage darf nie als implizite Live-Freigabe oder Strategie-Validierung interpretiert werden.
- Das lokale Archiv `docs/archive/docs_hub_snapshot/` ist nur noch ein optionaler historischer Rueckgriff.
- Externe Docs-Repo-Pfade sind kein produktiver Default mehr.

## Legacy Note

Die fruehere Docs-Hub-Struktur bleibt als Archiv referenzierbar, ist aber nicht mehr
die autoritative Quelle fuer laufende Arbeit in diesem Repo. Die aktuelle Canon-Matrix
steht in `docs/meta/WORKING_REPO_CANON.md`.
