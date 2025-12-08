# MCP-STACK BASELINE – DECISION DOC

## Zweck

Dieses Dokument legt die Basisarchitektur für alle MCP-Funktionen von Claire-de-Binare fest.

Es beantwortet:

- Welche MCP-Server gehören fix ins System?
- Wie werden sie gestartet?
- Wie greifen Orchestrator und Agenten darauf zu?

---

## Architektur-Prinzipien

1. **Single Entry Point**  
   Alle Clients (Claude, Cursor, ChatGPT Desktop etc.) sprechen ausschließlich mit dem  
   **Docker MCP Gateway** (`docker mcp gateway run`).:contentReference[oaicite:1]{index=1}  

2. **Preference für Standard-Server**  
   Wo immer möglich nutzen wir fertige MCP-Server aus dem Docker MCP Catalog  
   (Filesystem, GitHub, GitLab, Playwright, ggf. weitere wie Grafana später).  

3. **Custom nur für Domain-Logik**  
   Eigene MCP-Server sind nur erlaubt, wenn sie CDB-spezifische Aufgaben haben  
   (Agents-Sync, Domain-Logging, später Trading-/Analytics-spezifische Tools).:contentReference[oaicite:3]{index=3}  

4. **Tooling ist Infrastruktur, nicht Business-Logik**  
   Der Orchestrator sieht nur abstrakte Tools.  
   Die konkrete Auswahl der MCP-Server bleibt in dieser Architekturdatei dokumentiert.

---

## Fixer MCP-Basis-Stack

**Wird über Docker MCP Toolkit / Catalog aktiviert:**  

- `filesystem`  
  - Image: `mcp/filesystem`  
  - Zugriff auf:
    - `C:\Users\janne\Documents\Claire_de_Binare`
    - `C:\Users\janne\mcp_servers\logs`
  - Nur explizit konfigurierte Pfade sind verfügbar.:contentReference[oaicite:5]{index=5}  

- `github-official`  
  - Offizieller GitHub-MCP-Server aus dem Docker MCP Catalog.  
  - Verantwortlich für:
    - Branches, Commits, Pull Requests
    - Repo-Dateizugriffe
    - Automatisierung rund um Issues/PRs (z. B. für Copilot-/Agent-Workflows).

- `gitlab`  
  - GitLab MCP Server (HTTP-basiert direkt aus GitLab oder als Docker-Image wie `mcp/gitlab` / Community-Server).  
  - Verantwortlich für:
    - Projekte, Issues, Merge Requests, Labels
    - Pipelines/CI-Status (soweit exposed)
    - Primäre Projektsteuerung (GitLab = Source of Truth, GitHub = Second Source).  

- `playwright`  
  - Browser-Automation für:
    - Grafana / Prometheus Dashboards
    - Web-Recherche
    - Screenshots (Vision-Fähigkeit über das LLM).  

> GitLab und GitHub werden für Agenten symmetrisch angesprochen (gleiche Denklogik),  
> aber GitLab ist konzeptionell **Primary Forge**, GitHub **Secondary / Copilot-Workspace**.

---

## Custom CDB-MCP-Server

Diese Server sind projektspezifisch und laufen ebenfalls über den Gateway.:contentReference[oaicite:9]{index=9}  

- `agents-sync`  
  - Liefert Agenten-Rollen, Workflows und Governance-Regeln aus `AGENTS.md`  
    und den referenzierten Dateien (z. B. ORCHESTRATOR_Codex, Project_Visionary, Project_Visualizer, Stability_Guardian).

- `cdb-logger`  
  - Schreibt domänenspezifische Logs:
    - JSONL-Events (Agents, Repo, Trading)
    - Markdown-Logs (z. B. DECISION_LOG, SESSION_SUMMARY).

- `cdb-local-fs` (optional, geparkt)  
  - Wird nur reaktiviert, falls der Standard-Filesystem-Server funktional nicht ausreicht.

> Weitere Custom-Server (z. B. Trading-spezifische Backtesting-/Analytics-MCPs)  
> werden jeweils mit eigenem DECISION-Dokument ergänzt.

---

## Gateway-Konzept

- Alle oben genannten Server werden mit `docker mcp server enable ...` aktiviert.
- Der Start erfolgt immer über:

  ```bash
  docker mcp gateway run \
    --log-calls \
    --verify-signatures \
    --block-secrets
