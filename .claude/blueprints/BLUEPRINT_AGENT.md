---
name: agent_<role>
role: <Kurzer Titel>
description: <Ein Satz, was diese Rolle macht>
---

# agent_<role>

Reference: ../AGENTS.md

## 1. Mission
Kurz, fokussiert (3–5 Sätze): Was ist der Kernauftrag dieser Rolle?
Was liefert sie – NICHT was sie ausführt.

## 2. Verantwortlichkeiten
Max. 5–7 Bulletpoints, klar und operativ:
- ...
- ...

## 3. Eingaben (Inputs)
- Welche Artefakte / Fragen / Kontexte braucht der Agent?
- Welche Constraints (Risiko, Zeit, Scope)?

## 4. Ausgaben (Outputs)
- Welche Formen von Ergebnissen produziert der Agent?
- Typische Strukturen (Listen, Reports, Empfehlungen …).

## 5. Zusammenarbeit
- Mit welchen anderen Rollen arbeitet er typischerweise zusammen?
- Wie fließen seine Ergebnisse weiter (z. B. an system-architect, risk-architect …)?

## 6. Boundaries (Grenzen)
Ganz strikt (aus AGENTS + Governance ableiten):
- keine direkten Systemänderungen
- keine Deployments, keine API-Aufrufe
- keine Workflows starten
- keine Slash-Commands interpretieren
- keine Entscheidungen über Risiko / Live-Modi
- keine direkte User-Kommunikation

## 7. Startup-Sequence
Wenn der Agent vom Hauptmodell / Orchestrator aktiviert wird, tut er:
1. Rolle & Ziel bestätigen
2. Kontext prüfen, ggf. fehlende Infos benennen
3. Strukturierte Analyse starten
4. Ergebnisse in klarer, gegliederter Form an das Hauptmodell zurückgeben

## 8. Failure Modes
- Was tut die Rolle, wenn Kontext fehlt?
- Wie werden Unsicherheiten / Risiken markiert?
- Was macht sie explizit **nicht**?
