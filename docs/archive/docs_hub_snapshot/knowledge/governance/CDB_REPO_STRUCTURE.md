✅ FINALER TEXT – knowledge/governance/CDB_REPO_STRUCTURE.md

(1:1 ersetzen, ANHANG bleibt – aber als klar markiertes Legacy)

---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream:
    - knowledge/CDB_KNOWLEDGE_HUB.md
    - DOCS_HUB_INDEX.md
  status: canonical
  tags: [repo, structure, cleanroom, canonical]
---
# CDB_REPO_STRUCTURE
**Repository-Struktur & Cleanroom-Regeln (Canonical)**

Version: 1.2  
Status: Canonical

---

## 1. Ziel

Dieses Dokument definiert die **verbindliche Struktur** aller Repositories
im Projekt *Claire de Binare*.

Ziel ist:
- klare Trennung von **Ausführung** und **Wissen**
- Vermeidung von Repo-Verschmutzung
- deterministische Builds
- agentensichere Arbeitsflächen

---

## 2. Grundprinzip (nicht verhandelbar)

> **Ein Repo = eine Funktion.**

Es gibt **keine Mischformen**.

---

## 3. Repos im System

### 3.1 Working Repo — *Execution Only*
**Beispiel:** `Claire_de_Binare`

Zweck:
- Runtime
- Code
- Infrastruktur
- Tests

Erlaubte Inhalte:


/core
/services
/infrastructure
/tests
/tools
/scripts
docker-compose*.yml
Makefile
README.md


Verboten:
- `/knowledge`
- `/governance`
- `/agents`
- Logs, Reports, Entscheidungsdokumente
- KI-Kontexte oder Prompts

> Dieses Repo darf **jederzeit gelöscht und neu gebaut** werden können.

---

### 3.2 Docs Hub Repo — *Canon & Knowledge*
**Beispiel:** `Claire_de_Binare_Docs`

Zweck:
- Governance
- Knowledge
- Agenten
- Logs
- Memory

Struktur:


/governance
/knowledge
/agents
/logs
/_legacy_quarantine
DOCS_HUB_INDEX.md


Regel:
- **Docs Hub ist Canon**
- Chat, Sessions, KI-Ausgaben sind es nicht

---

## 4. Schreibregeln (hart)

| Bereich | Schreibrecht |
|------|-------------|
| knowledge/governance/ | ❌ niemand (außer User) |
| knowledge/ | ✅ Agenten + User |
| agents/ | ❌ (nur explizit) |
| logs/ | ✅ strukturiert |
| Working Repo | ❌ ohne Delivery-Gate |

Write-Gates werden durch:
- Policies
- CI
- Review erzwungen

---

## 5. Agent Cleanroom

Agenten:
- **lesen Canon**
- **schreiben nicht in Canon**
- erzeugen temporäre Artefakte nur in:
  - `.cdb_agent_workspace/` (gitignored)

Kein Agent darf:
- fehlende Dateien anlegen
- Strukturen „reparieren“
- Konventionen erraten

---

## 6. Migration & Altlasten

Alte oder unklare Dateien:
- kommen nach `/_legacy_quarantine`
- sind **nicht aktiv**
- werden nicht interpretiert

---

## 7. Durchsetzung

Verstöße gegen diese Struktur gelten als:
- Governance-Bruch
- CI-Fehler
- Systeminkonsistenz

---

## ANHANG — Historisch / Legacy (nicht aktiv)

Dieser Abschnitt dient **ausschließlich** der Nachvollziehbarkeit
früherer Struktur-Entscheidungen.

- Keine operative Relevanz
- Kein Canon
- Keine Ableitungen

Bei Unsicherheit gilt:
> **Hauptteil schlägt Anhang.**
