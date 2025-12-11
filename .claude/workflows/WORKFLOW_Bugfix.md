# WORKFLOW_Bugfix (Optimiert, Agenten-Minimalismus)

## Ziel
Schnelle, sichere Behebung eines klar abgegrenzten Fehlers mit minimalem Agenteneinsatz.

## Rollen
- Hauptmodell  
- test-engineer  
- code-reviewer  
- refactoring-engineer  
- system-architect  
- documentation-engineer  

## Phase A – Analyse (read-only)
1. Claude sammelt Kontext (Issue, Logs, relevante Files).
2. system-architect prüft Architektur-Impact (nur falls relevant).
3. test-engineer identifiziert/ergänzt Tests, die den Bug reproduzieren.
4. refactoring-engineer bewertet, ob strukturelle Anpassungen sinnvoll/notwendig sind.
5. Claude erstellt Analyse-Report (IST, Ursache, SOLL, Risiken, Testplan).

## Phase B – Delivery (User-Go)
1. Branch erstellen (`bugfix/<kurze-beschreibung>`).
2. test-engineer schreibt/aktualisiert Tests (Red).
3. refactoring-engineer / Hauptmodell implementieren Fix + nötige Refactors (Green).
4. code-reviewer prüft Qualität, Stil, Risiko, Seiteneffekte.
5. documentation-engineer aktualisiert relevante Doku (Changelog, README, AKTUELLER_STAND, falls nötig).
6. Claude erzeugt PR mit:
   - Zusammenfassung
   - Risiko-Assessment
   - Testübersicht
   - ggf. Rollback-Hinweis

## Erfolgsindikatoren
- Bug reproduzierbar vor Fix, nicht reproduzierbar nach Fix  
- Tests dokumentieren das Verhalten klar  
- PR klein, fokussiert, gut begründet  
- Keine unerwünschten Seiteneffekte in angrenzenden Bereichen
