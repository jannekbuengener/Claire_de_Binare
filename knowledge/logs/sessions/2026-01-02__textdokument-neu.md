# Archived Content: Textdokument (neu).txt

**Date:** 2026-01-02
**Source:** Textdokument (neu).txt

## Content
GO:MERGE (PR #25)

Pre-Merge Gate (2 Minuten, strikt):

1) Quarantäne/Secrets:
- Bestätige, dass ca.crt und client.crt NICHT im Repo gelandet sind.
- Im PR darf es maximal geben:
  - MD/YAML Manifest/Stub (Hash + externer Pfad + rationale)
  - Snapshot/Log in knowledge/logs/sessions/
- Keine *.crt/*.key/*.pfx/*.pem im Diff.

2) .gitignore Scope:
- Prüfe, dass .gitignore nur klar lokale/generated Sachen ignoriert.
- Kein “catch-all” wie: *.md, knowledge/**, *.yml global, oder komplette Ordner wie tools/ pauschal.
- Wenn zu breit: STOP und schlage eine präzisere Regel vor.

3) Governance/Policy Touch:
- Bestätige: keine Änderungen in knowledge/governance/* und agents/* (außer evtl. ledger, falls überhaupt nötig).
- Wenn doch: STOP und begründen.

Wenn alle 3 Gates PASS:
- Squash Merge ist ok.
- Post-Merge:
  - checkout main + pull --ff-only
  - Branch löschen
  - git status -sb muss clean sein

Output:
- Bestätigung “Merged PR #25”
- Finaler git status -sb
- 1-Zeiler: was ignoriert, was migriert, was gelöscht (Counts)

