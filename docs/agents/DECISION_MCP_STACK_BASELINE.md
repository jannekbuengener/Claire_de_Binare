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
   **Docker MCP Gateway** (`docker mcp gateway run`).

2. **Preference für Standard-Server**  
   Wo immer möglich nutzen wir fertige MCP-Server aus dem Docker MCP Catalog  
   (Filesystem, GitHub, Playwright).

3. **Custom nur für Domain-Logik**  
   Eigene MCP-Server sind nur erlaubt, wenn sie CDB-spezifische Aufgaben haben  
   (Agents-Sync, Domain-Logging, später Trading-spezifische Tools).

4. **Tooling ist Infrastruktur, nicht Business-Logik**  
   Der Orchestrator sieht nur abstrakte Tools.  
   Die konkrete Auswahl der MCP-Server bleibt in dieser Architekturdatei dokumentiert.

---

## Fixer MCP-Basis-Stack

**Wird über Docker MCP Toolkit aktiviert:**

- `filesystem`  
  - Image: `mcp/filesystem`  
  - Zugriff auf:
    - `C:\Users\janne\Documents\Claire_de_Binare`
    - `C:\Users\janne\mcp_servers\logs`
  - Nur explizit konfigurierte Pfade sind verfügbar.

- `github-official`  
  - Offizieller GitHub-MCP-Server.  
  - Verantwortlich für Branches, Commits, Pull Requests, Repo-Dateizugriffe.

- `playwright`  
  - Browser-Automation für:
    - Grafana / Prometheus
    - Web-Recherche
    - Screenshots (Vision-Fähigkeit über das LLM).

---

## Custom CDB-MCP-Server

Diese Server sind projektspezifisch und laufen ebenfalls über den Gateway.

- `agents-sync`  
  - Liefert Agenten-Rollen, Workflows und Governance-Regeln aus `AGENTS.md` und den referenzierten Dateien.

- `cdb-logger`  
  - Schreibt domänenspezifische Logs:
    - JSONL-Events (Agents, Repo, Trading)
    - Markdown-Logs (z. B. DECISION_LOG, SESSION_SUMMARY).

- `cdb-local-fs` (optional, geparkt)  
  - Wird nur reaktiviert, falls der Standard-Filesystem-Server funktional nicht ausreicht.

---

## Gateway-Konzept

- Alle oben genannten Server werden mit `docker mcp server enable ...` aktiviert.
- Der Start erfolgt immer über:

  ```bash
  docker mcp gateway run \
    --log-calls \
    --verify-signatures \
    --block-secrets
  ```

- Der Gateway ist der **einzige** MCP-Endpunkt in den Clients.

---

## Auswirkungen auf Agenten & Orchestrator

- Orchestrator-Prompts dürfen nur auf folgende Server Bezug nehmen:
  - `agents-sync`
  - `filesystem`
  - `github-official`
  - `playwright`
  - `cdb-logger`
- `hub-mcp` und `mcp-registry` werden nicht mehr aktiv verwendet.  
  Die Funktionen „Hub“ und „Registry“ übernimmt der Docker MCP Gateway + Catalog.
