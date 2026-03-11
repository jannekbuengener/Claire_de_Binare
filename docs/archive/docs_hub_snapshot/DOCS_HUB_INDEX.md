---
role: navigation
status: canonical
domain: docs_hub
type: index
relations:
  purpose: central_navigation
  scope: docs_hub_repository
---

# DOCS_HUB_INDEX
**Canonical Index — Claire de Binare Docs Hub**

Status: Canonical  
Rolle: Single Source of Truth (Docs Hub)

---

## 1. Zweck

Dieses Dokument ist der **kanonische Index** des *Claire de Binare* Dokumentations-Hubs.

### Contributor Guardrails

This repo blocks Git merge-conflict markers in docs files via CI (`Docs Conflict Guard`).
Local quick check (PowerShell):
`pwsh -Command "Select-String -Path agents\**\*.md,knowledge\**\*.md,meta\**\*.md -Pattern '^\s*<<<<<<<.*$','^\s*=======$','^\s*>>>>>>>.*$' -AllMatches"`

If the command prints nothing, you’re good.

Es dient als:
- primärer Einstiegspunkt für Agenten
- Navigationshilfe für Menschen
- Referenz für Struktur, Zuständigkeiten und Grenzen

Der Docs Hub ist **autoritativer** als:
- Chat-Kontext
- Session-Logs
- Working-Repos

---

## 2. Grundprinzipien (verbindlich)

- Docs Hub = **Canon**
- Working Repo = **Execution**
- Kein Agent erzeugt neue Canon-Dateien ohne explizite Freigabe
- Fehlende Dateien werden **nicht** automatisch angelegt
- Struktur schlägt Vollständigkeit

---

## 3. Verzeichnisstruktur (kanonisch)

### `/agents/`
**Zweck:** Definition, Steuerung und Grenzen aller KI-Agenten

- `agents/AGENTS.md` → Gemeinsame Agenten-Grundordnung (Canonical)
- `agents/CLAUDE.md` → Session Lead / Orchestrator
- `agents/GEMINI.md` → Audit & Review
- `agents/roles/CODEX.md` → Deterministische Ausführung
- `agents/COPILOT.md` → Assistenz / Komfort

#### Unterordner
- `agents/roles/` → Rollendefinitionen
- `agents/policies/` → Agentenrelevante Policies
- `agents/charters/` → Charter-Dokumente
- `agents/prompts/` → Prompt-Artefakte
- `agents/tasklists/` → Agenten-Tasklisten

---

### `/knowledge/governance/`
**Zweck:** Höchste Regel- und Autoritätsebene

Wichtige Dateien:
- `CDB_CONSTITUTION.md` → oberste Instanz
- `CDB_GOVERNANCE.md` → operative Governance
- `CDB_AGENT_POLICY.md` → Agenten-Mandate & Grenzen
- `CDB_REPO_STRUCTURE.md` → Zielstruktur Repos
- `NEXUS.MEMORY.yaml` → kanonisches Langzeitgedächtnis

Governance schlägt **alles** außer Verfassung.

---

### `/knowledge/`
**Zweck:** Wissen, Entscheidungen, Arbeitsgedächtnis, Logs

Kern-Dateien:
- `CDB_KNOWLEDGE_HUB.md`  
  → Entscheidungs- und Übergabe-Hub (Canonical, non-governance)

- `SYSTEM.CONTEXT.md`  
  → Laufzeit- & Umweltkontext (Read-Only)

- `SHARED.WORKING.MEMORY.md`  
  → Temporärer Denkraum (Non-Canonical)

Weitere Unterordner:
- `knowledge/operating_rules/` → Betriebsregeln
- `knowledge/reviews/` → Audit- & Review-Berichte
- `knowledge/tasklists/` → Aufgabenlisten
- `knowledge/logs/` → Logs & Reports
- `.dev_freeze_status` → Entwicklungs-Freeze-Status

---

### `/logs/`
**Zweck:** Roh-Logs, Berichte, technische Artefakte  
Kein Canon. Keine Entscheidungen.

---

### `/_legacy_quarantine/`
**Zweck:** Ablage für:
- veraltete
- unklare
- zu prüfende Dateien

Nichts hier ist aktiv oder kanonisch.

---

## 4. Deprecated / Migration

Diese Dateien gelten als **deprecated** und dürfen nicht mehr verwendet werden:
- `copilot.md`
- `codex.md`
- `claude.md`

Ersatz:
- Agenten-Dateien unter `/agents/`
- Prompts unter `/agents/prompts/`
- Tasklisten unter `/agents/tasklists/` oder `/knowledge/tasklists/`

---

## 5. Lese-Pflicht für Agenten (Autoload)

Jeder Agent **MUSS** bei Start laden:
1. `DOCS_HUB_INDEX.md`
2. `agents/AGENTS.md`
3. `knowledge/CDB_KNOWLEDGE_HUB.md`
4. relevante Governance-Dateien

Wenn ein Dokument fehlt: **STOP & melden**.

---

## Abschluss

Dieser Index definiert **wie das System gelesen wird**.  
Wer ihn ignoriert, arbeitet **außerhalb des Systems**.
