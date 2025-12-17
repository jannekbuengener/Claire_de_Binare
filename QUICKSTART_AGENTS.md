# 🤖 Agent Quick Start Guide

**Problem gelöst**: "Warum kommt denn Codex und Claude nicht?"

## TL;DR - Sofort-Lösung

### Für lokale Entwicklung (Windows/WSL2):

```bash
# 1. API-Keys setzen
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# 2. Status prüfen
make agent-status

# 3. Fertig - Agenten sind einsatzbereit
```

### Für CI/CD oder andere Umgebungen:

```bash
# 1. CI-Config aktivieren (ersetzt externe Windows-Pfade)
make agent-config-ci

# 2. API-Keys als Umgebungsvariablen oder Secrets setzen
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# 3. Validieren
make agent-validate
```

---

## Was war das Problem?

### Root Cause
1. **Nicht-existente Modelle**: `mcp-config.toml` referenzierte Platzhalter-Modelle (`gpt-5.1-codex-max`, `copilot/gpt-5-codex-mini`)
2. **Externe Pfade**: Konfiguration nutzte `/local-docs/` Mount-Punkte, die nur lokal auf Windows existieren
3. **Fehlende Dokumentation**: Keine Anleitung zur Agent-Aktivierung

### Lösung
- ✅ **CI-Config erstellt**: `mcp-config.ci.toml` mit repo-internen Pfaden
- ✅ **Dokumentation**: `AGENT_SETUP.md` mit vollständiger Anleitung
- ✅ **Makefile-Targets**: Automatisierung für Config-Wechsel und Validierung
- ✅ **Klarstellung**: Lokale Config verwendet Platzhalter-Namen (für Testing), Production benötigt echte API-Keys

---

## Agent-Rollen im Überblick

| Agent | Rolle | Schreibrecht | Aktivierung |
|-------|-------|--------------|-------------|
| **Claude** | Session Lead & Orchestrator | `CDB_KNOWLEDGE_HUB.md` | Immer aktiv |
| **Codex** | Code-Executor | Keine | Auf Anforderung |
| **Gemini** | Auditor & Reviewer | `CDB_KNOWLEDGE_HUB.md` (Audit) | Bei Reviews |
| **Copilot** | Assistenz | Keine | Optional |

---

## Modell-Namen für Production

### Claude (Session Lead, Gemini)
- ✅ `claude-3-5-sonnet-20241022` (empfohlen)
- ✅ `claude-3-opus-20240229` (höhere Qualität)

### OpenAI (Codex, Copilot)
- ✅ `gpt-4-turbo-preview` (empfohlen)
- ✅ `gpt-4` (stabiler)
- ⚠️ `gpt-3.5-turbo` (nur für Copilot)

**Wichtig**: In `mcp-config.toml` die Zeilen `model = ...` und `model_fast = ...` anpassen!

---

## Makefile-Befehle (Cheat Sheet)

```bash
# Hilfe anzeigen
make agent-help

# Status prüfen (welche Config ist aktiv?)
make agent-status

# Config wechseln
make agent-config-local    # Windows/WSL2 mit externen Mounts
make agent-config-ci       # Linux/CI/CD mit repo-internen Pfaden

# Validierung
make agent-validate        # Prüft Config + Agent-Definitionen + API-Keys

# Dokumentation
make agent-docs           # Zeigt AGENT_SETUP.md
```

---

## Governance-Compliance

Gemäß `CDB_AGENT_POLICY.md`:

### ✅ Erlaubt (Write-Gates)
- `CDB_KNOWLEDGE_HUB.md`
- `.cdb_agent_workspace/*` (temporär, gitignored)

### ❌ Verboten
- `/core`, `/services`, `/infrastructure`, `/tests`
- `/governance/*`
- Tresor-Zone
- Secrets, Keys, Custody

### Autonomie-Zonen
- **Zone A (Autonom)**: Architektur-Varianten, Analysen
- **Zone B (Review)**: Strukturelle Vorschläge
- **Zone C (Vorschlag)**: Grenzbereiche, mehrdeutige Governance
- **Zone D (Verboten)**: Tresor, Hard Limits, Canonical Policies

---

## Troubleshooting

### "API-Keys nicht gefunden"
```bash
# Prüfen
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Setzen (Bash/Zsh)
export ANTHROPIC_API_KEY="sk-ant-..."

# Setzen (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### "Externe Pfade /local-docs/ nicht gefunden"
```bash
# Lösung: CI-Config verwenden
make agent-config-ci
```

### "Modell nicht gefunden"
```bash
# mcp-config.toml öffnen und model = ... anpassen
# Siehe "Modell-Namen für Production" oben
```

---

## Weitere Ressourcen

- 📖 **Vollständige Dokumentation**: `AGENT_SETUP.md`
- 📋 **Agent-Definitionen**: `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, `COPILOT.md`
- 🔒 **Governance**: `governance/CDB_AGENT_POLICY.md`
- 🧠 **Memory**: `governance/NEXUS.MEMORY.yaml`
- 📝 **Knowledge Hub**: `CDB_KNOWLEDGE_HUB.md`

---

**Status**: v1.0 • 2024-12-17  
**Problem gelöst**: Agent-Integration dokumentiert und CI-tauglich gemacht ✅
