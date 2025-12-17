# Agent-Setup: Claude, Codex, Gemini, Copilot

## Problem: "Warum kommt denn Codex und Claude nicht?"

### Übersicht

Dieses Dokument erklärt, wie die KI-Agenten (Claude, Codex, Gemini, Copilot) im CDB-Projekt konfiguriert und aktiviert werden.

---

## Agent-Rollen (gemäß CLAUDE.md, CODEX.md, GEMINI.md, COPILOT.md)

### 1. Claude (Session Lead & Orchestrator)
- **Rolle**: Session Lead, Koordination, Planung, finale Entscheidungen
- **Aufgaben**: Architektur, Governance-Compliance, Agenten-Orchestrierung
- **Schreibrecht**: Nur `CDB_KNOWLEDGE_HUB.md`
- **Aktivierung**: Primärer Agent, immer aktiv

### 2. Codex (Code-Executor)
- **Rolle**: Deterministisches Ausführungsmodell für Code
- **Aufgaben**: Code-Erzeugung, Refactoring, Performance-Optimierung
- **Aktivierung**: Nur auf explizite Anforderung durch Claude
- **Einschränkungen**: Kein Governance-Zugriff, kein Systemverständnis

### 3. Gemini (Auditor & Reviewer)
- **Rolle**: Unabhängiger Auditor
- **Aufgaben**: Governance-Compliance, Risiko-Analyse, Reviews
- **Schreibrecht**: Nur `CDB_KNOWLEDGE_HUB.md` (Audit-Notes)
- **Aktivierung**: Bei Architektur-, Risiko- oder Governance-Änderungen

### 4. Copilot (Assistenz)
- **Rolle**: Nicht-kritisches Assistenzmodell
- **Aufgaben**: Code-Vervollständigung, Syntax-Checks, Boilerplate
- **Einschränkungen**: Kein Systemkontext, keine Governance
- **Aktivierung**: Optional, jederzeit entfernbar

---

## Technische Konfiguration

### MCP-Konfigurationsdateien

Das Projekt verwendet zwei MCP-Konfigurationsdateien:

1. **`mcp-config.toml`** (Lokale Windows-Entwicklung)
   - Für Windows 11 + WSL2 optimiert
   - Verwendet externe Mount-Punkte (`/local-docs/`)
   - Platzhalter-Modellnamen für lokale Entwicklung

2. **`mcp-config.ci.toml`** (CI/CD & Production)
   - Für Linux-Umgebungen optimiert
   - Verwendet repo-interne Pfade
   - Produktions-Modelle: `claude-3-5-sonnet-20241022`, `gpt-4`

### Umgebungsvariablen

Für die Aktivierung der Agenten werden folgende API-Keys benötigt:

```bash
# Für Claude (Session Lead, Gemini)
export ANTHROPIC_API_KEY="sk-ant-..."

# Für Codex, Copilot (optional)
export OPENAI_API_KEY="sk-..."
```

---

## Aktivierung der Agenten

### Lokale Entwicklung (Windows + WSL2)

1. **Konfiguration prüfen**:
   ```bash
   cat mcp-config.toml
   ```

2. **API-Keys setzen**:
   ```powershell
   # In PowerShell
   $env:ANTHROPIC_API_KEY = "sk-ant-..."
   $env:OPENAI_API_KEY = "sk-..."
   ```

3. **Externe Mounts sicherstellen**:
   - Pfad `/local-docs/` muss gemountet sein
   - Alternativ: In `mcp-config.toml` auf repo-interne Pfade umstellen

### CI/CD & Production

1. **CI-Konfiguration verwenden**:
   ```bash
   cp mcp-config.ci.toml mcp-config.toml
   ```

2. **API-Keys als Secrets setzen** (GitHub Actions):
   ```yaml
   env:
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
   ```

3. **Agenten aufrufen**:
   ```bash
   # Claude als Session Lead
   claude --config mcp-config.ci.toml

   # Codex für Code-Generation (via Claude)
   # Claude delegiert automatisch an Codex bei Code-Tasks
   ```

---

## Agent-Workflow (gemäß CDB_KNOWLEDGE_HUB.md)

### Standard-Delegationspfade

#### Pfad A – Umsetzung (Copilot / Codex)
1. Claude definiert Scope + Akzeptanzkriterien
2. Claude erstellt Tasklist
3. Claude weist zu:
   - **Copilot**: Wenn Umsetzung direkt klar ist
   - **Codex**: Wenn Analyse / Varianten nötig sind
4. Executor liefert Ergebnis
5. Claude entscheidet final

#### Pfad B – Review (Gemini)
1. Claude definiert Review-Ziel
2. Claude verweist auf Review-Checkliste
3. Gemini liefert Findings (MUST / SHOULD / NICE)
4. Claude entscheidet über Umsetzung

---

## Troubleshooting

### Problem: "Codex und Claude kommen nicht"

**Root Cause**:
- `mcp-config.toml` referenziert nicht-existente Modelle (`gpt-5.1-codex-max`, `copilot/gpt-5-codex-mini`)
- Externe Pfade `/local-docs/` funktionieren nicht in CI/CD-Umgebung
- API-Keys nicht gesetzt

**Lösung**:
1. **Modell-Namen korrigieren**:
   - Claude: `claude-3-5-sonnet-20241022` oder `claude-3-opus-20240229`
   - GPT-4: `gpt-4-turbo-preview` oder `gpt-4`

2. **Pfade anpassen**:
   - Für CI/CD: `mcp-config.ci.toml` verwenden
   - Für lokale Entwicklung: Externe Mounts sicherstellen oder repo-interne Pfade nutzen

3. **API-Keys setzen**:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export OPENAI_API_KEY="sk-..."
   ```

### Problem: Agent-Delegation funktioniert nicht

**Check-List**:
- [ ] Ist `CLAUDE.md` Session Start Protocol geladen?
- [ ] Sind `governance/NEXUS.MEMORY.yaml` und `CDB_KNOWLEDGE_HUB.md` verfügbar?
- [ ] Ist das Agent-Handshake-System konfiguriert?
- [ ] Sind Write-Rechte korrekt (nur `CDB_KNOWLEDGE_HUB.md`)?

---

## Governance-Compliance

### Write-Gates (CDB_AGENT_POLICY.md)

KI darf persistent schreiben **nur** in:
- `CDB_KNOWLEDGE_HUB.md`
- `.cdb_agent_workspace/*` (lokal, gitignored)

KI darf **nicht** schreiben in:
- `/core`, `/services`, `/infrastructure`, `/tests`
- `/governance/*`
- Tresor-Zone

### Autonomie-Zonen (CDB_AGENT_POLICY.md)

- **Zone A (Autonom)**: Architektur-Varianten, Refactor-Optionen, Analysen
- **Zone B (Autonom mit Review)**: Strukturelle Vorschläge, Policy-Verbesserungen
- **Zone C (Vorschlag)**: Grenzbereiche, mehrdeutige Governance-Interpretationen
- **Zone D (Verboten)**: Tresor, Hard Limits, Canonical Policies, Execution ohne Risk-Layer

---

## Weitere Ressourcen

- **CLAUDE.md**: Claude Session Lead & Orchestrator Spezifikation
- **CODEX.md**: Codex Code-Generator Spezifikation
- **GEMINI.md**: Gemini Auditor & Reviewer Spezifikation
- **COPILOT.md**: Copilot Assistenz-Modell Spezifikation
- **CDB_AGENT_POLICY.md**: Governance-Regeln für Agenten
- **CDB_KNOWLEDGE_HUB.md**: Zentrale Entscheidungs- und Handoff-Drehscheibe
- **governance/NEXUS.MEMORY.yaml**: Kanonisches System-Memory

---

**Status**: v1.0 • 2024-12-17  
**Maintainer**: Jannek (Session Owner)
