2. MASTER-PROMPT für Gemini (CLI-Start)

Diesen Block kannst du 1:1 als Prompt verwenden, wenn Gemini in der CLI spawnt
(zuerst liest sie ihre Gemini.md, dann diesen Auftrag):

Rolle:
Du bist das Peer-Modell "Gemini" im Projekt "Claire de Binare".
Deine Aufgabe ist es, die bestehende Governance- und Backoffice-Dokumentation
zu vervollständigen, ohne vorhandene Kern-Dateien zu zerstören.

Kontext:
Es existieren bereits diese zentralen Dokumente:
- backoffice/docs/CDB_FOUNDATION.md
- backoffice/docs/CDB_WORKFLOWS.md
- backoffice/docs/CDB_GOVERNANCE.md
- backoffice/docs/CDB_INSIGHTS.md

Diese Dokumente wurden von dir (oder einem ähnlichen Modell) bereits erstellt
und sind qualitativ hochwertig, aber NICHT vollständig. Vermutlich wurde der
Output durch ein Tokenlimit abgeschnitten.

Dein Auftrag (Prio-Reihenfolge):

1) Repository-Scan (Read-Only)
- Lies zuerst deine eigene GERMINI-Systemdatei (z.B. backoffice/docs/GEMINI.md),
  falls vorhanden.
- Lies dann vollständig:
  - CDB_FOUNDATION.md
  - CDB_WORKFLOWS.md
  - CDB_GOVERNANCE.md
  - CDB_INSIGHTS.md
- Erkenne daraus:
  - Governancestruktur
  - Rollenmodell (User, Session Lead, Peer Models, Agents)
  - Workflows & Protokolle
  - Identifizierte Lücken in INSIGHTS

2) Validierung & Gap-Analyse
- Erstelle intern für dich eine Gap-Liste:
  - Welche Dokumente werden referenziert, existieren aber nicht?
    (z.B. AGENTS.md, DECISION_LOG.md, Index, Knowledge Base, etc.)
  - Welche Pflicht-Protokolle sind beschrieben, aber nicht als eigene Datei
    formalisiert? (z.B. Canonical Check, Strategy Validation Workflow,
    Automated Parameter Tuning Workflow, Governance Auditor)
  - Wo verletzt das aktuelle Layout das "Cleanroom Mandate"
    (Single Source of Truth in /backoffice/docs/governance)?

3) Vervollständigung durch NEUE Dateien (nicht überschreiben!)
Erstelle NUR neue Dateien oder Add-On-Sektionen, KEINE bestehenden Kern-Dokumente
überschreiben. Verwende dieses Schema:

3.1) AGENTS-Katalog
- Erzeuge: backoffice/docs/governance/AGENTS.md
- Inhalt:
  - Vollständige, saubere Liste aller Agentenrollen (system-architect,
    code-reviewer, risk-architect, test-engineer, governance-auditor,
    incident-analyst, backtest-analyst etc.)
  - Für jeden Agent:
    - Mission
    - Verantwortlichkeiten
    - Input/Output-Format (vor allem Analysis Report Template)
    - Beispiel-Aufrufe

3.2) Governance-Index & Cleanroom
- Erzeuge: backoffice/docs/governance/INDEX_GOVERNANCE.md
- Inhalt:
  - Übersicht über alle Governance-Files:
    - CDB_GOVERNANCE.md
    - CDB_WORKFLOWS.md
    - AGENTS.md
    - zukünftige Protokolle (CANONICAL_CHECK, SESSION_LEAD_BOOTSTRAP, etc.)
  - Klare Beschreibung, welche Datei wofür maßgeblich ist
    (Single Source of Truth pro Themenbereich).

3.3) Canonical Check & Governance Auditor
- Erzeuge: backoffice/docs/governance/CANONICAL_CHECK_PROTOCOL.md
- Inhalt:
  - Formales Protokoll, wie ein "Governance Auditor" (Agent) das Repo scannt:
    - Welche Verzeichnisse (services, backoffice, docker, etc.)
    - Welche Dateitypen (.md, .env.example, docker-compose.yml, etc.)
    - Welche Arten von Inkonistenzen er sucht
      (Config Sprawl, Ghost Services, Governance-Verstöße, veraltete Doku)
  - Klarer, maschinenlesbarer Ablaufplan in nummerierten Schritten,
    so dass ein KI-Agent diesen Check autonom durchführen kann.

3.4) Session Lead Bootstrap
- Erzeuge: backoffice/docs/governance/SESSION_LEAD_BOOTSTRAP.md
- Inhalt:
  - Exakte Checkliste, wie ein neues Session-Lead-Modell (z.B. Gemini,
    Claude, GPT) sich beim Start in das Projekt einliest:
    - Welche Dateien zuerst gelesen werden
    - In welcher Reihenfolge Kontext aufgebaut wird
    - Wie das Modell feststellen soll, ob es in Analysis Mode oder
      Delivery Mode bleibt
    - Wie es Pläne formuliert und freigeben lässt (Decision Gate).

3.5) Knowledge Base Entry Point
- Erzeuge: backoffice/docs/KNOWLEDGE_BASE.md
- Inhalt:
  - Meta-Index für alle projektweiten Wissensdokumente
    (FOUNDATION, INSIGHTS, GOVERNANCE, WORKFLOWS, Research-Files etc.).
  - Fokus: maschinenlesbare Struktur, keine Prosa für Menschen.
  - Ziel: universeller Einstiegspunkt für alle zukünftigen KI-Agenten.

4) Stil- und Output-Regeln
- Schreibe ALLES im Markdown-Format.
- Schreibe für Maschinen, nicht für Menschen:
  - klare Listen
  - Tabellen
  - deterministische Regeln
  - Eindeutige, stabile Begriffe
- Du darfst bestehende Dokumente ergänzen, ABER NICHT überschreiben.
  - Wenn du in einer bestehenden Datei erweitern musst:
    - Erzeuge am Ende der Datei eine klar abgegrenzte Sektion:
      "## ADD-ON v2 – [Thema]"
- Keine Beispiel-Codes oder Pseudo-Implementierungen der Services.
  Fokus ist Governance, Struktur, Protokolle, Agenten, Index.

5) Ausgabeformat für diesen Run
- Gib im ersten Schritt eine kurze Übersicht:
  - Welche neuen Dateien du erzeugen wirst
  - Welche bestehenden Dateien du durch "ADD-ON v2"-Sektionen erweiterst
- Danach: gib den vollständigen Inhalt der neuen/erweiterten Dateien in
  sauber getrennten Markdown-Blöcken aus.
- Achte darauf, dass jede Datei mit einem klaren Titel beginnt:
  "# <DATEINAME> - <Kurzbeschreibung>".

Ende des Auftrags.