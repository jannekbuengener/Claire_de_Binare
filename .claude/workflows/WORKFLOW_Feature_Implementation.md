# WORKFLOW_Feature_Implementation (Optimiert, Agenten-Minimalismus)

## Ziel
Implementierung eines neuen Features oder einer Erweiterung mit klarer Architektur, Tests und minimiertem Risiko.

## Rollen
- Hauptmodell  
- system-architect  
- code-reviewer  
- test-engineer  
- devops-engineer  
- documentation-engineer  

## Phase A – Analyse & Design (read-only)
1. Claude sammelt Anforderungen, bestehende Doku, relevante Codepfade.
2. system-architect entwirft Architektur-/Design-Vorschlag (Datenfluss, Schnittstellen, Grenzen).
3. test-engineer definiert Teststrategie (Unit, Integration, E2E, ggf. Staging-Plan).
4. devops-engineer prüft Infrastruktur-Implikationen (Deploy, Config, Feature Flags).
5. Claude erstellt Analyse- & Design-Report inkl. Risiken und Alternativen.

## Phase B – Delivery (User-Go)
1. Branch erstellen (`feature/<kurze-beschreibung>`).
2. Umsetzung des Features nach Design-Vorschlag.
3. test-engineer implementiert/aktualisiert Tests und führt sie aus.
4. code-reviewer prüft Codequalität, Architektur-Alignment, Risiken.
5. devops-engineer bereitet Deploy-Pfade, Feature-Flags und Rollback-Strategie vor (falls relevant).
6. documentation-engineer aktualisiert Nutzer- und Systemdoku.
7. Claude erstellt PR inkl.:
   - Feature-Beschreibung
   - technischem Überblick
   - Testnachweisen
   - Deploy-/Rollback-Hinweisen

## Erfolgsindikatoren
- Feature erfüllt Anforderungen (funktional & nicht-funktional)  
- Tests stabil, reproduzierbar, automatisiert  
- Architektur konsistent mit Systemvorgaben  
- PR klar, nachvollziehbar, risiko-bewusst
