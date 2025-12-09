# RISK-MODE-DEFINITIONS

Dieses Dokument beschreibt die verschiedenen Betriebsmodi des Systems
und legt für jeden Modus klare Grenzen fest. Es geht dabei um:
- wie viel Risiko pro Tag,
- wie viele Positionen,
- welche Beträge maximal bewegt werden,
- und wann das System stoppen muss.

## 1. Übersicht der Modi

- Paper-Mode: Nur Simulation, keine echten Orders.
- Safe-Mode: Sehr vorsichtiger Echtbetrieb mit kleinen Beträgen.
- Live-Mode: Voller Echtbetrieb unter klaren Regeln.

## 2. Paper-Mode (Simulation)

- Live-Geld: Nein
- Ziel: Verhalten beobachten, Fehler finden, Einstellungen testen
- Max. Risiko: Nur virtuell
- Stop-Kriterien:
  - Beispiel: X Tage in Folge Verlust
  - Beispiel: Unerwartetes Verhalten im Log

(Details werden später ergänzt.)

## 3. Safe-Mode (Echtbetrieb mit kleinen Beträgen)

- Live-Geld: Ja, aber klein
- Ziel: System im echten Markt testen
- Max. Verlust pro Tag:
- Max. Verlust pro Woche:
- Max. Positionsgröße:
- Stop-Kriterien:
  - …

(Diese Felder werden bewusst erst nach ersten Paper-Tests gefüllt.)

## 4. Live-Mode (voller Betrieb)

- Live-Geld: Ja, normaler Einsatz
- Ziel: Produktiver Einsatz
- Voraussetzungen:
  - Paper-Mode stabil
  - Safe-Mode stabil
  - Rollback-Mechanismus vorhanden

(Konkrete Werte werden erst festgelegt, wenn du mit den Tests zufrieden bist.)

## 5. Allgemeine Stop-Kriterien (für alle Modi)

Hier werden später die Bedingungen gesammelt, bei denen das System
automatisch anhalten oder in einen sicheren Modus wechseln muss.
