# Issue Triage & Backlog Hygiene (2025-12-25)

## TL;DR
Backlog muss die Realität spiegeln. Obsolete Issues killen Velocity.

## Kanonische Label-Sprache

Die offizielle Status-/Triage-Taxonomie ist in `.github/LABELS.md` und
`.github/workflows/labels.json` definiert:

- **Status:** `status:ready`, `status:blocked`, `status:in-review`, `status:wontfix`
- **Triage:** `triage:offen` (offenes Item ohne Milestone)

Alte Labels wie `status:idea`, `status:approved` usw. sind nicht kanonisch.
Project-v2-Statuswerte (`Backlog`, `Ready`, etc.) sind Board-Feldwerte, keine Labels.

## Triage SOP
1) Ist das Issue noch reproduzierbar im aktuellen main?
2) Gibt es bereits einen E2E/Test/Replay Contract, der es abdeckt?
3) Wenn obsolet: kommentieren mit Evidence + schließen.
4) Wenn teilweise: in Phasen splitten (Model / Integration / E2E / Docs).

## Beispiel (Risk Guards)
- Phase 1: Models + Unit tests
- Phase 2: Service integration + config
- Phase 3: E2E cases + CI evidence
