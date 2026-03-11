# PIF-9 / PIF-10 Prompt-Framework  
## Failure- & Recovery-Modelle für event-getriebene Trading-Systeme

---

## Zweck dieses Dokuments

Dieses Dokument beschreibt **einen klaren, wiederverwendbaren Prompt-Rahmen** für  
**PIF-9 (Analyse & Strukturierung)** und **PIF-10 (Entscheidung & Systemdesign)**  
mit Fokus auf **Failure- & Recovery-Modelle in event-getriebenen Trading-Systemen**.

Ziel:  
Yannick soll damit **eigene Prompts sauber, deterministisch und governance-fähig** bauen können, ohne jedes Mal bei Null anzufangen.

---

## Grundannahmen (nicht diskutabel)

- Event-Driven Architecture  
- Event Sourcing als State-Quelle  
- Determinismus > Performance  
- Recovery ist **Design-Pflicht**, kein Sonderfall  
- Kein impliziter State, keine stillen Retries

---

# PIF-9 — Analyse- & Struktur-Prompt  
*(Denken, nicht Entscheiden)*

## Einsatzgebiet

- Systemanalyse  
- Fehlermodell-Katalogisierung  
- Recovery-Optionen sammeln  
- Abhängigkeiten sichtbar machen  
- Risiken explizit machen  

**Kein Design-Freeze, keine Umsetzung.**

---

## PIF-9 Prompt-Template

```text
Du agierst als Systemarchitekt für deterministische, event-getriebene Trading-Systeme.

AUFGABE:
Analysiere Failure- & Recovery-Modelle für ein event-getriebenes Trading-System.

SYSTEMRAHMEN:
- Event-Driven Pipeline (Market → Signal → Risk → Execution → Result)
- Event Sourcing als Single Source of Truth
- Services sind stateless, States entstehen ausschließlich aus Events
- Kein globaler Lock, keine impliziten Retries

ANALYSE-SCHWERPUNKTE:
1. Failure-Typen
   - Datenfehler
   - Infrastruktur-Ausfälle
   - Logik-/Policy-Verletzungen
   - Zeit- & Reihenfolgefehler
   - Externe Abhängigkeiten (Exchange, Netzwerk)

2. Failure-Ort
   - Ingress (Market Data)
   - Processing (Signal / Risk)
   - Execution
   - Persistence
   - Replay / Recovery

3. Auswirkungen
   - deterministisch / nicht-deterministisch
   - reversibel / irreversibel
   - lokal / systemweit

4. Recovery-Optionen
   - Retry
   - Replay
   - Snapshot-Rollback
   - Graceful Degradation
   - Hard Stop / Kill-Switch

OUTPUT-FORMAT:
- Strukturierte Liste
- Klare Trennung von:
  • Beobachtung  
  • Risiko  
  • Recovery-Mechanismus  
- Keine Design-Entscheidungen
- Keine Implementierung
- Keine Bewertung, nur Analyse

ZIEL:
Vollständiger Failure-/Recovery-Katalog als Entscheidungsgrundlage.
