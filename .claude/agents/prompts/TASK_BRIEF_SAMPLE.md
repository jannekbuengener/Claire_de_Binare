# Codex Task Brief – Einrichtung der gemeinsamen Agentenbasis

**Task title:**  
Einrichtung einer einheitlichen Agentenbasis (AGENT_BASE) für Claire de Binare

**Business goal / why now:**  
Ziel ist eine modellunabhängige Agentenarchitektur für Codex & Claude.  
Dadurch entsteht ein klares, wartbares und reproduzierbares System aus Orchestrator und Unteragenten, das als Fundament für alle zukünftigen Entwicklungs-, Analyse- und Risk‑Aufgaben dient.

**Scope (in):**  
- Erstellung der Ordnerstruktur `docs/agent_base/`  
- Rollen‑Definitionen (Orchestrator + Unteragenten)  
- Workflow‑Dokumente  
- Governance & Rechte  
- Prompt‑Vorlagen  
- Interlinking aller Dokumente

**Out-of-scope:**  
- Keine Änderungen am produktiven Trading-Code  
- Keine Docker-/Infra‑Modifikationen  
- Keine Risk‑ oder Mode‑Parameteränderungen  
- Kein Live‑Trading‑Einfluss

**Desired workflow:**  
Analyse + Umsetzung in einem Durchlauf, ausschließlich im Dokumentationsbereich.  
Anschließend strukturierter Abschlussreport.

**Constraints:**  
- Nur Arbeiten an Markdown-Dateien  
- Keine externe API‑Nutzung  
- Idempotent und reproduzierbar  
- Struktur kompatibel für Codex & Claude  
- Englisch als Standard‑Dokusprache

**Risk sensitivity / mode:**  
Paper‑Mode / Meta‑Konfigurationsänderung  
Keine produktiven Risiken.

**Success criteria / KPIs:**  
- `docs/agent_base/AGENTS.md` existiert und dient als Single Source of Truth  
- Alle Rollen, Workflows, Governance‑ und Promptdateien konsistent verlinkt  
- Orchestrator‑Prompt ist sofort einsatzbereit  
- Strukturreport erstellt

**Testing expectations:**  
Kein Code‑Test nötig, nur struktureller Self‑Check durch Codex im Abschlussreport.

**Dependencies / impacted areas:**  
- Betroffen: `docs/agent_base/`  
- Unberührt: Services, Backoffice, Docker, Execution

**Timeline / priority:**  
Priorität: Hoch  
Soll vor allen Architektur- und Refactoring-Aufgaben stehen.

**Attachments / links:**  
Projekt: Claire de Binare  
Zentrale Dateien: (falls vorhanden) PROJEKT_BESCHREIBUNG.md, AKTUELLER_STAND.md
