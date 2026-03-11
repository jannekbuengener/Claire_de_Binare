Du agierst als Lead-Architekt für ein produktives, deterministisches,  
event-getriebenes Trading-System mit Audit- und Governance-Pflicht.

AUSGANGSLAGE:  
Ein vollständiger Failure-/Recovery-Katalog liegt vor.

AUFGABE:  
Definiere verbindliche Failure- & Recovery-Modelle.

ENTSCHEIDUNGSREGELN:  
\- Determinismus schlägt Verfügbarkeit  
\- Recovery muss reproduzierbar sein  
\- Jeder Recovery-Pfad ist auditierbar  
\- Kein stilles Fehlermanagement  
\- Kein automatischer Kapital-Risiko-Übergang

ZU DEFINIEREN:  
1\. Zulässige Failure-Typen  
2\. Erlaubte Recovery-Mechanismen pro Failure  
3\. Verbotene Automatiken  
4\. Hard Stops & Kill-Switch-Trigger  
5\. Replay- & Snapshot-Strategie  
6\. Governance-Eskalation (wann Mensch eingreift)

FORMAT:  
\- Klare Regeln (keine Prosa)  
\- MUST / SHOULD / FORBIDDEN  
\- Jede Regel mit Begründung  
\- Keine Alternativen offen lassen  
\- Keine Implementierungsdetails

ZIEL:  
Ein konsistentes, durchsetzbares Recovery-Regelwerk,  
das deterministisch replay-fähig ist.  
Typischer Output von PIF-10  
Klare Recovery-Policy

Keine Grauzonen

Direkte Ableitbarkeit für:

Code

Tests

CI-Guards

Audit-Reports

Zusammenspiel PIF-9 ↔ PIF-10  
Phase	Zweck	Ergebnis  
PIF-9	Denken	Vollständigkeit  
PIF-10	Entscheiden	Verbindlichkeit

PIF-9 ohne PIF-10 \= Analyse-Endlosschleife  
PIF-10 ohne PIF-9 \= blinder Aktionismus

Best Practice für Yannick  
Nie mischen

Erst PIF-9 komplett

Dann PIF-10 in separater Session

Ergebnisse versionieren

PIF-10 Outputs als Policy oder ADR behandeln

Kurzfassung  
PIF-9 \= Verstehen aller Fehler

PIF-10 \= Festlegen, wie das System damit umgeht

Recovery ist Architektur, kein Patch

Determinismus ist das Leitmotiv

\# PIF-9 / PIF-10 Prompt-Framework    
\#\# Failure- & Recovery-Modelle für event-getriebene Trading-Systeme

\---

\#\# Zweck dieses Dokuments

Dieses Dokument beschreibt \*\*einen klaren, wiederverwendbaren Prompt-Rahmen\*\* für    
\*\*PIF-9 (Analyse & Strukturierung)\*\* und \*\*PIF-10 (Entscheidung & Systemdesign)\*\*    
mit Fokus auf \*\*Failure- & Recovery-Modelle in event-getriebenen Trading-Systemen\*\*.

Ziel:    
Yannick soll damit \*\*eigene Prompts sauber, deterministisch und governance-fähig\*\* bauen können, ohne jedes Mal bei Null anzufangen.

\---

\#\# Grundannahmen (nicht diskutabel)

\- Event-Driven Architecture    
\- Event Sourcing als State-Quelle    
\- Determinismus \> Performance    
\- Recovery ist \*\*Design-Pflicht\*\*, kein Sonderfall    
\- Kein impliziter State, keine stillen Retries

\---

\# PIF-9 — Analyse- & Struktur-Prompt    
\*(Denken, nicht Entscheiden)\*

\#\# Einsatzgebiet

\- Systemanalyse    
\- Fehlermodell-Katalogisierung    
\- Recovery-Optionen sammeln    
\- Abhängigkeiten sichtbar machen    
\- Risiken explizit machen  

\*\*Kein Design-Freeze, keine Umsetzung.\*\*

\---

\#\# PIF-9 Prompt-Template

\`\`\`text  
Du agierst als Systemarchitekt für deterministische, event-getriebene Trading-Systeme.

AUFGABE:  
Analysiere Failure- & Recovery-Modelle für ein event-getriebenes Trading-System.

SYSTEMRAHMEN:  
\- Event-Driven Pipeline (Market → Signal → Risk → Execution → Result)  
\- Event Sourcing als Single Source of Truth  
\- Services sind stateless, States entstehen ausschließlich aus Events  
\- Kein globaler Lock, keine impliziten Retries

ANALYSE-SCHWERPUNKTE:  
1\. Failure-Typen  
   \- Datenfehler  
   \- Infrastruktur-Ausfälle  
   \- Logik-/Policy-Verletzungen  
   \- Zeit- & Reihenfolgefehler  
   \- Externe Abhängigkeiten (Exchange, Netzwerk)

2\. Failure-Ort  
   \- Ingress (Market Data)  
   \- Processing (Signal / Risk)  
   \- Execution  
   \- Persistence  
   \- Replay / Recovery

3\. Auswirkungen  
   \- deterministisch / nicht-deterministisch  
   \- reversibel / irreversibel  
   \- lokal / systemweit

4\. Recovery-Optionen  
   \- Retry  
   \- Replay  
   \- Snapshot-Rollback  
   \- Graceful Degradation  
   \- Hard Stop / Kill-Switch

OUTPUT-FORMAT:  
\- Strukturierte Liste  
\- Klare Trennung von:  
  • Beobachtung    
  • Risiko    
  • Recovery-Mechanismus    
\- Keine Design-Entscheidungen  
\- Keine Implementierung  
\- Keine Bewertung, nur Analyse

ZIEL:  
Vollständiger Failure-/Recovery-Katalog als Entscheidungsgrundlage.  
