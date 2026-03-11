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

## Operating Rules

- `AGENTS.md` im Repo-Root ist nur ein Pointer auf diese Datei.
- Agenten und Tools sollen standardmaessig lokale Pfade im Working Repo verwenden.
- Das lokale Archiv `docs/archive/docs_hub_snapshot/` ist nur noch ein optionaler historischer Rueckgriff.
- Externe Docs-Repo-Pfade sind kein produktiver Default mehr.

## Legacy Note

Die fruehere Docs-Hub-Struktur bleibt als Archiv referenzierbar, ist aber nicht mehr
die autoritative Quelle fuer laufende Arbeit in diesem Repo. Die aktuelle Canon-Matrix
steht in `docs/meta/WORKING_REPO_CANON.md`.
