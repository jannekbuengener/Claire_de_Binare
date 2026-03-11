---
relations:
  role: knowledge_base
  domain: knowledge
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/NEXUS.MEMORY.yaml
    - knowledge/governance/CDB_REPO_STRUCTURE.md
  downstream:
    - agents/
---
# CDB_KNOWLEDGE_HUB
**Shared Decisions & Agent Handoffs**

Version: 1.1  
Status: Canonical (non-governance)

---

## EXECUTIVE SNAPSHOT (read-only)

Stand: 2025-12-15  
Gültig bis: explizites Update

**Projekt:** Claire de Binare (CDB)  
**Systemstatus:** stabile Infrastruktur-Baseline erreicht

### Kernergebnisse
- Trennung **Working Repo / Docs Hub** ist final
- Agenten sind kanonischer Bestandteil des Docs-Repos
- PR-Block 01–06 vollständig umgesetzt und gepusht
- GitLab CI aktiv (CI-Guard, Write-Zone-Checks)
- Unit-Test-Baseline vorhanden
- Modulare Compose-Architektur (base / dev / prod)
- Determinismus-Hooks für Replay vorbereitet

> Dieser Snapshot ist **kein Live-Status**.  
> Er ist ein komprimierter Zustandsanker für neue Sessions und Agenten.

---

## 0. Zweck & Einordnung

Der **CDB_KNOWLEDGE_HUB** ist der **zentrale, versionierte Entscheidungs- und Übergabe-Hub**
für alle KI-gestützten Sessions im Projekt *Claire de Binare*.

Er ist ausdrücklich **nicht**:
- Governance
- System-Memory
- Session-Log
- Task-Tracker
- technische Dokumentation

Er ist der Ort für:
- bestätigte Entscheidungen
- agentenübergreifende Handoffs
- verdichtete Session-Ergebnisse

---

## 1. Ground Rules (verbindlich)

### Schreibrechte
- Claude: ✅ (als Session Lead)
- Gemini: ✅ (Reviews / Handoffs)
- Copilot / Codex: ❌
- User: ✅ jederzeit

### Inhaltliche Regeln
- Keine Secrets
- Kein Roh-Code
- Keine vollständigen Logs
- Immer Referenzen auf Artefakte (Pfad, Commit, MR)

### Verhältnis zu Memory
- Dieser Hub ist **kein Memory**
- Kein automatischer Übergang nach `NEXUS.MEMORY`
- Memory-Kandidaten müssen explizit markiert und freigegeben werden

---

## 2. Repo-Topologie (kanonisch)

### 2.1 Working Repo – `Claire_de_Binare`
**Zweck:** Ausführung, Runtime, Build

Erlaubt:
- core/
- services/
- infrastructure/
- tools/
- scripts/
- tests/
- README.md, Makefile, docker-compose*.yml

Verboten:
- knowledge/
- knowledge/governance/
- agents/
- Logs oder Dokumentation

---

### 2.2 Docs Hub – `Claire_de_Binare_Docs`
**Zweck:** Wissen, Governance, Agenten, Logs

```text
knowledge/
├─ CDB_KNOWLEDGE_HUB.md
├─ SHARED.WORKING.MEMORY.md
├─ SYSTEM.CONTEXT.md
├─ CURRENT_STATUS.md
├─ governance/
│  ├─ CDB_CONSTITUTION.md
│  ├─ CDB_GOVERNANCE.md
│  ├─ CDB_AGENT_POLICY.md
│  └─ NEXUS.MEMORY.yaml
├─ roadmap/
│  └─ EXPANDED_ECOSYSTEM_ROADMAP.md
├─ logs/
│  ├─ sessions/
│  └─ weekly_reports/
├─ operating_rules/
├─ reviews/
└─ tasklists/

agents/
├─ AGENTS.md
├─ CLAUDE.md
├─ CODEX.md
├─ COPILOT.md
├─ GEMINI.md
├─ AUTOLOAD_MANIFEST.yaml
└─ setup/
   └─ roles/ (Pointer-Dateien)

legacy_quarantine/
```

---

## 3. Agent Handoffs

Übergaben zwischen Agenten / Sessions

Konvention:

OPEN

INPROGRESS

DONE (mit Referenz)

Aktuelle Handoffs

[DONE] Codex → Claude: P1-Developer-Tools geliefert (2025-12-14)

[OPEN] Claude → Services: get_secret()-Migration (P2)

[OPEN] Gemini → Claude: Governance-Review Rückmeldung ausstehend

4. Decision Log (kanonisch)

Regel:

Entscheidungen gelten bis explizit revidiert

Kein implizites Überschreiben

Aktive Entscheidungen

2025-12-15 – Repo-Topologie final

Working Repo ≠ Docs Hub

Referenzen: CDB_REPO_STRUCTURE.md, WORKING_REPO_INDEX.md

2025-12-15 – Agents sind kanonisch

Ort: /agents im Docs Hub

2025-12-15 – SHARED.WORKING.MEMORY ist nicht-kanonisch

Zweck: Denken, kein Wissen

2025-12-14 – P1 Developer-Tools produktionsreif

cdb-stack-doctor.ps1

cdb-service-logs.ps1

cdb-secrets-sync.ps1

2025-12-27 – M7-M9 Roadmap Refinement Complete (Issue #107)

Epic #91 breakdown: M7 Testnet (4-6 weeks, 10 issues consolidated)

M8 Security critical blockers: Security Lead + Pentest Booking ($10k-$30k)

M9 Release: 2-3 weeks, SLA targets defined (99.9% uptime, <100ms p50 latency)

Roadmaps: knowledge/roadmap/M7_TESTNET_PLAN.md (393 lines), M8_SECURITY_PLAN.md (386 lines), M9_RELEASE_PLAN.md (356 lines)

Critical Path validated: M6 ✅ → M7 🔄 → M8 → M9

Referenz: GitHub Issue #107

2025-12-19 – Agent Roles bleiben extern (external-only policy)

Alle Agent-Definitionen außerhalb der Repositories

.claude/agents/ aus Working Repo entfernt (20 Dateien)

Externe Location: C:\Users\janne\Documents\GitHub\Workspaces\agents

Referenz: GitHub Issue #133, Commit 8a417ee

5. Session Summaries (verdichtet)

2025-12-18/19 – Governance Hygiene Enforcement (COMPLETE)

Ziel: Systematische Governance Compliance via Multi-Agent Koordination

Ergebnis: 6 Issues abgeschlossen (#132 Meta, #133 .claude/agents/, #134 CODEOWNERS, #8 tasklists/, #9 .txt Migration, #10 PROMPT_CODEX.txt)

Handoff: Issue #11 (MEGA-ISSUE) aufbrechen in Subtasks

Status: Phase 1 komplett, External-Only Policy durchgesetzt, Working Repo & Docs Hub sauber

Referenz: GitHub jannekbuengener/Claire_de_Binare #132 (Meta-Issue geschlossen)

2025-12-13A – T1-Migration

Ziel: Altstruktur entfernen

Ergebnis: t1/ vollständig bereinigt

Handoff: Technische Validierung offen

2025-12-12A – Docker-Architektur (Gordon)

Modulare Compose-Strategie bestätigt

PostgreSQL / Redis / Monitoring spezifiziert

2025-12-12B – Gemini-Migrationsreview

Status: APPROVED WITH CONDITIONS

Kritisch: Git-History-Validierung erforderlich

6. Session Notes Archive (Detail)

Vollständige technische Details, Analysen, Risiken
Kein Status, keine Entscheidungen

(Sessions 2025-12-12A / 12B / 13B / 14A unverändert übernommen)

7. Claude Tasklist – Delivery Plan (CDB)

Reihenfolge ist bewusst gewählt: früher Value, wenig Risiko

PR-01 — CI-Guard (MUST)
PR-02 — Safe Deletes (MUST)
PR-03 — Makefile Fix (MUST)
PR-04 — Unit-Test Skeletons (SHOULD)
PR-05 — Compose Base/Dev Split (SHOULD)
PR-06 — Replay-Enabler (SHOULD)

Stop-Regel:

Wenn Unsicherheit entsteht → stoppen und fragen.

8. Delegation (Kurzreferenz)

Die vollständige Delegationsanweisung liegt unter:

knowledge/OPERATING_RULES/CLAUDE_DELEGATION_POLICY.md


Dieser Hub enthält keine operativen Delegationsdetails mehr.

9. Abschluss

Dieser Hub ist:

Entscheidungsanker

Übergabepunkt

Session-Verdichtung

Er ist kein Live-Status, kein Memory, keine Governance.