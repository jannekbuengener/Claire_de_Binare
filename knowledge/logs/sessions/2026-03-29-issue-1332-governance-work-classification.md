# Session Log — Issue #1332: governance_*_work Classification

**Datum**: 2026-03-29
**Branch**: `fix/1332-governance-work-classification`
**PR**: #1341
**Commit**: `ce04d10`

## Befund

- 7 `governance_*_work/`-Verzeichnisse (~373 Dateien) existieren lokal
- Inhalt: agent-generierte Issue-Snapshots, tmp-Bodies, Caches, Python-Scripts (Codex governance passes)
- Nie committed, 0 tracked files
- Bereits via `.git/info/exclude` (Zeilen 30–37) ausgeschlossen
- Docs-Hub-Referenzen: ausschließlich in frozen JSON-Snapshots von Issue #748 Body-Text — kein aktiver/irreführender Verweis
- ripgrep respektiert `.git/info/exclude` → kein Drift-Sweep-Lärm vom Repo-Root

## Klassifikation (alle 7)

- `governance_core_pack_work/` (83 Dateien) → `historical-generated-keep`
- `governance_core_status_report_work/` (36 Dateien) → `historical-generated-keep`
- `governance_evidence_backfill_work/` (43 Dateien) → `historical-generated-keep`
- `governance_evidence_backfill_pass2_work/` (103 Dateien) → `historical-generated-keep`
- `governance_evidence_pass21_work/` (28 Dateien) → `historical-generated-keep`
- `governance_evidence_pass35_work/` (18 Dateien) → `historical-generated-keep`
- `governance_evidence_pass3_targeted_work/` (62 Dateien) → `historical-generated-keep`

## Maßnahme

- `.gitignore`: `governance_*_work/` Glob ergänzt (portabler Schutz, vorher nur `.git/info/exclude`)
- Keine inhaltlichen Edits an den Verzeichnissen — frozen Snapshots brauchen keine Textbereinigung

## Validierung

- `git check-ignore -v` bestätigt: `.gitignore:185` greift für alle 7 Verzeichnisse
- `rg` vom Repo-Root findet keine Treffer in diesen Verzeichnissen
- 0 tracked files betroffen

## Follow-up

- #1336: Kein separater Eintrag nötig — Glob deckt Muster vollständig ab
