# WORKFLOW_Risk_Mode_Change (Optimiert, Agenten-Minimalismus)

## Ziel
Sicheres Ändern des Betriebsmodus (Paper → Live, Limit-Anpassungen) unter strikten Governance- & Risk-Kontrollen.

## Rollen
- Hauptmodell  
- risk-architect  
- devops-engineer  
- test-engineer  

## Phase A – Analyse (read-only)
1. Claude erstellt Request-Dossier.
2. risk-architect bewertet Exposure + Limits.
3. devops-engineer prüft technische Umschaltbarkeit.
4. test-engineer definiert sicherheitsrelevante Checks.
5. Claude erzeugt Analyse-Report im Standardformat.

## Phase B – Delivery (User-Go)
1. risk-architect gibt grünes Licht.
2. devops-engineer führt Änderungen durch.
3. test-engineer validiert mit Smoke Tests.
4. Claude überwacht Stop-Kriterien.
5. Rollback, falls Schwellenwerte verletzt werden.

## Outputs
- Approval-Report  
- Testprotokoll  
- Doku-Update
