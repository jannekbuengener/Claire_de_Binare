# MCP / NotebookLM – Nutzungsregel für Gemini (CDB)

## Status
Draft – operational guideline  
Gültig für: Gemini (Audit & Research Agent)

---

## Zweck

Der MCP-Server `notebooklm-mcp` dient ausschließlich als **Evidenz- und Research-Quelle**.
Er ersetzt **keine** kanonischen Dokumente, Governance oder Entscheidungen.

NotebookLM ist **Input**, nicht Autorität.

---

## Erlaubte Nutzung (ALLOWED)

Gemini DARF NotebookLM über MCP nutzen für:

- quellenübergreifende Analyse mehrerer Research-Dokumente
- Identifikation von:
  - wiederkehrenden Thesen
  - impliziten Systemannahmen
  - Redundanzen
  - Widersprüchen oder Spannungen
- Synthesis zur Vorbereitung von:
  - Promotion-Entscheidungen
  - ADRs (Architecture Decision Records)
  - Governance- oder Architektur-Reviews

Pflicht:
Jede relevante Aussage MUSS auf konkrete NotebookLM-Quellen rückführbar sein.

---

## Verbotene Nutzung (NOT ALLOWED)

Gemini DARF NICHT:

- Canon-, Governance- oder Policy-Dokumente verändern
- Entscheidungen treffen oder vorwegnehmen
- Inhalte aus NotebookLM als „gesetzt“ deklarieren
- neue Regeln, Prinzipien oder Invarianten einführen
- NotebookLM als Single Source of Truth behandeln

---

## Output-Standard (verbindlich)

Jeder MCP-basierte Output MUSS enthalten:

- expliziten Hinweis: „MCP / NotebookLM genutzt“
- klare Trennung von:
  - Finding
  - Quelle(n)
  - Bedeutung für CDB
- Kennzeichnung von Erkenntnissen,
  die ohne MCP nicht möglich gewesen wären

Keine impliziten Annahmen.  
Keine unmarkierten Schlussfolgerungen.

---

## Entscheidungsgrenze

- Gemini liefert **Evidenz und Analyse**
- Entscheidungen trifft ausschließlich:
  - Claude (Session Lead)
  - oder der User (Jannek)

NotebookLM-Findings sind zitierfähig und prüfbar,
aber **niemals automatisch bindend**.

---

## Begründung

Diese Regel stellt sicher, dass:

- MCP maximalen Mehrwert liefert
- Canon und Governance nicht verwässert werden
- Research auditierbar und reproduzierbar bleibt

KI bleibt Werkzeug – nicht Autorität.
