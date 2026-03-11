---
relations:
  role: doc
  domain: agents
  upstream:
    - agents/README.md
  downstream:
    - agents/agent_orga/AGENT_QUICKSTART.md
    - agents/agent_orga/AGENT_SETUP_GUIDE.md
    - agents/agent_orga/PLAN_AGENT_DOCS_ORCHESTRATION.md
---

# Agent Orga — Cockpit

Hier startet man, wenn man **arbeiten** will: Setup, Ablauf, Orga-Entscheidungen.  
Die **kanonischen Rollen** leben in `agents/roles/`.

## Startpfad (empfohlen)

1) **Sofort loslegen:** [AGENT_QUICKSTART.md](./AGENT_QUICKSTART.md)  
2) **Technik & Governance sauber:** [AGENT_SETUP_GUIDE.md](./AGENT_SETUP_GUIDE.md)  
3) **Docs-/Agent-Orchestrierung (Meta):** [PLAN_AGENT_DOCS_ORCHESTRATION.md](./PLAN_AGENT_DOCS_ORCHESTRATION.md)

## Operating Model (kurz)

- **Canon für Rollen:** `agents/roles/`  
- **Prompts:** `agents/prompts/`  
- **HV-Spezialfälle:** `agents/HV/`  
- **Orga/Setup/Plan:** `agents/agent_orga/`

## „Wo ändere ich was?“ (Decision Table)

- Rolle, Mandat, Grenzen eines Agents → `agents/roles/<AGENT>*.md`  
- Prompt-Text, Varianten, Templates → `agents/prompts/`  
- High-Voltage / Sonder-Workflows → `agents/HV/`  
- Einstieg, Setup, Orga-Prozess → `agents/agent_orga/` (hier)

## Minimaler Qualitäts-Check (bevor Commit)

- Links in `agents/README.md` + `agent_orga/README.md` klickbar
- Rollen-Dateien verweisen auf Canon (keine Dopplungen)
- Prompts sind pro Agent klar benannt (ein Zweck pro Datei)
