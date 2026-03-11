# Issue Triage & Backlog Hygiene (2025-12-25)

## TL;DR
Backlog muss die Realität spiegeln. Obsolete Issues killen Velocity.

## Triage SOP
1) Ist das Issue noch reproduzierbar im aktuellen main?
2) Gibt es bereits einen E2E/Test/Replay Contract, der es abdeckt?
3) Wenn obsolet: kommentieren mit Evidence + schließen.
4) Wenn teilweise: in Phasen splitten (Model / Integration / E2E / Docs).

## Beispiel (Risk Guards)
- Phase 1: Models + Unit tests
- Phase 2: Service integration + config
- Phase 3: E2E cases + CI evidence
