# WORKFLOW_PAPER_TRADING_TEST
3-Tage-Testlauf im Paper-Trading-Modus  
Ziel: Das echte Verhalten des Systems beobachten, bevor Entscheidungen getroffen werden.

## 1. Ziel
Drei Tage lang soll das System komplett ohne Eingriffe laufen.
Wir wollen sehen:
- Wie verhält es sich in echten Marktphasen?
- Welche Signale sind stabil, welche springen?
- Gibt es Muster, Fehler, Ausreißer?
- Wo muss Donnerfly optimiert werden?

## 2. Testaufbau
- Modus: Paper-Trading
- Laufzeit: 72 Stunden am Stück
- Keine manuellen Eingriffe
- Monitoring aktiv
- Logging vollständig anschalten

## 3. Was wir beobachten
Während der drei Tage achten wir auf:
- Verhalten bei Trend und Seitwärtsphasen
- Reaktionen auf starke Bewegungen (Volatilität)
- Wie oft das System recht hat vs. wie oft es sich korrigieren muss
- Ob es zu vorsichtig oder zu aggressiv agiert
- Wo Donnerfly Entscheidungen doppelt prüft oder zu langsam ist

## 4. Daten, die gesammelt werden
- Alle Orders (virtuell)
- Alle Signale
- Alle Positionswechsel
- Zeitstempel, Indikatoren, Scores
- Fehler, Warnungen, Abbrüche

## 5. Auswertung nach den 3 Tagen
Am Ende beantworten wir:
- Was funktioniert gut?
- Was funktioniert gar nicht?
- Welche Muster wiederholen sich?
- Welche Limits wären sinnvoll?
- Wo fehlen klare Stop-Kriterien?
- Was muss Donnerfly als Erstes lernen?

## 6. Ergebnis
Dieses Dokument dient als Basis für:
- Optimierung von Donnerfly
- Vorbereitung der späteren Governance
- Definition realistischer Risiko-Grenzen
- Übergang in Safe-Mode (nur wenn stabil)
