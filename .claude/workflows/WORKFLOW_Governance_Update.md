# WORKFLOW_Governance_Update (Optimiert)

## Ziel
Governance-Dokumentation (AGENTS.md, Rollen, Workflows) konsistent, schlank und aktuell halten.

## Rollen (minimal)
- Hauptmodell  
- documentation-engineer  

## Phase A – Analyse

1. Claude extrahiert neue Rollen/Änderungen aus der Session.
2. Abgleich mit:
   - `AGENTS.md`
   - Governance-Dokumenten
3. Gap-Analyse:
   - Neue Rollen?
   - Geänderte Verantwortlichkeiten?
   - Anpassungen in Workflows notwendig?
4. Claude erstellt Analyse-Report + Vorschlag für Updates.

## Phase B – Delivery (nur nach User-Go)

1. Branch erstellen (`governance-update-YYYYMMDD`).
2. `AGENTS.md` aktualisieren; neue Rollen/Workflows hinzufügen.
3. documentation-engineer pflegt DECISION_LOG mit Governance-Entscheidungen.
4. PR erstellen.

## Erfolgsindikatoren
- Governance spiegelt reale Agenten-Rollen & Workflows korrekt wider.
- DECISION_LOG enthält klare und vollständige Entscheidungen.
