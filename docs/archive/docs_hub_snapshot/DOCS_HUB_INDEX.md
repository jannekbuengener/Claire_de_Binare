---
role: navigation
status: archived
domain: docs_hub_snapshot
type: index
relations:
  purpose: historical_navigation
  scope: archived_docs_hub_content
---

# DOCS_HUB_INDEX (Archived)
**Historical Index — Claire de Binare Docs Hub Snapshot**

Status: Archived (read-only)
Context: This file was the canonical index of the former standalone Docs Hub repository. The split-repo model was retired in #1140. All active documentation now lives in the working repo (`Claire_de_Binare`). This file is preserved as a historical navigation aid for the local archive snapshot only.

Current canonical layout: see `docs/meta/WORKING_REPO_CANON.md`.

---

## 1. Zweck (historisch)

Dieses Dokument war der kanonische Index des ehemaligen Dokumentations-Hubs.
Es dient jetzt nur noch als historischer Navigationsanker fuer das lokale Archiv unter `docs/archive/docs_hub_snapshot/`.

### Contributor Guardrails (historisch)

The old docs repo blocked Git merge-conflict markers via CI (`Docs Conflict Guard`).
This guard applied to the standalone docs repo, not to the consolidated working repo.

---

## 2. Grundprinzipien (historisch — nicht mehr aktiv)

Die folgenden Prinzipien galten im Split-Repo-Modell und sind nach #1140 nicht mehr massgeblich:

- Docs Hub war Canon (jetzt: Working Repo ist Canon)
- Working Repo war nur Execution (jetzt: Working Repo ist Canon + Execution)
- Kein Agent erzeugt neue Canon-Dateien ohne explizite Freigabe (unveraendert als allgemeines Prinzip)

---

## 3. Verzeichnisstruktur (historisch)

Die folgende Struktur beschreibt den Zustand des ehemaligen Docs Hub zum Zeitpunkt des Snapshots. Aktive Versionen dieser Inhalte leben jetzt unter den entsprechenden Working-Repo-Pfaden.

### `/agents/`
- `agents/AGENTS.md` — jetzt lokal unter `agents/AGENTS.md`
- `agents/CLAUDE.md`, `agents/GEMINI.md`, `agents/roles/CODEX.md`, `agents/COPILOT.md`
- Unterordner: `roles/`, `policies/`, `charters/`, `prompts/`, `tasklists/`

### `/knowledge/governance/`
- `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` etc.
- Jetzt lokal unter `knowledge/governance/`

### `/knowledge/`
- `CDB_KNOWLEDGE_HUB.md`, `SYSTEM.CONTEXT.md`, `SHARED.WORKING.MEMORY.md`
- Jetzt lokal unter `knowledge/`

### `/logs/`
Roh-Logs und technische Artefakte. Kein Canon.

### `/_legacy_quarantine/`
Veraltete und zu pruefende Dateien. Nichts hier ist aktiv oder kanonisch.

---

## 4. Deprecated / Migration (historisch)

Die folgenden Dateien waren bereits im alten Docs Hub deprecated:
- `copilot.md`, `codex.md`, `claude.md`

---

## 5. Lese-Pflicht (historisch — nicht mehr aktiv)

Die Autoload-Pflicht galt fuer den ehemaligen Docs Hub. Im konsolidierten Working Repo gelten die Entrypoints aus `docs/meta/WORKING_REPO_CANON.md`.

---

## Abschluss

Dieser Index ist ein historisches Artefakt. Die aktuelle Systemnavigation wird durch `docs/meta/WORKING_REPO_CANON.md` und die Working-Repo-Entrypoints definiert.
