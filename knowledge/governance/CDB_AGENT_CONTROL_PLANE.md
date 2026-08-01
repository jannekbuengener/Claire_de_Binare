---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md
  downstream:
    - agents/AGENTS.md
    - docs/skills/cdb-pr-router/SKILL.md
  status: canonical
  tags: [agents, control-plane, authority, lifecycle, evidence]
---

# CDB Agent Control Plane

Status: Canonical  
Version: `cdb-agent-control-plane/v1`  
Issue: `#4250`  
Parent: `#4249`  
Authority class: Architecture and governance contract (docs/canon only)

## 1. Zweck, Scope und Nicht-Ziele

### 1.1 Zweck

Die **CDB Agent Control Plane (ACP)** ist der provider-neutrale Steuerrahmen
für governed Agentenläufe im Claire-de-Binare-Repository. CDB bleibt die
Autorität für Routing, Contracts, Gates und Merge. Ausführungsprovider
(zuerst Cursor) führen zugewiesene Arbeit aus, autorisieren aber weder Merge
noch Live-Trading.

### 1.2 Scope dieses Canon-Dokuments

Dieses Dokument definiert:

- Architektur und Systemgrenzen der ACP
- Authority Matrix je Komponente
- Governed Run Lifecycle inkl. terminaler Semantik
- Evidence-Grenzen (Brain vs. Agent Run vs. Targeted Slice vs. Final CI)
- Zero-Click-/Bootstrap-Regeln und Capability-Drift
- Lineage zu bestehenden Routing-, Delivery-/Merge- und Final-CI-Verträgen

### 1.3 Nicht-Ziele (verbindlich)

- Kein Dispatcher-, Registry-, Provider-Adapter- oder Execution-Contract-Schema
  (Follow-ups `#4251`–`#4257`; dieses Dokument nimmt deren Schemata nicht vorweg)
- Kein Ersatz und keine Umbenennung der **GitHub Workflow Control Plane**
  (`.github/CONTROL_PLANE.md`, `#1640`/`#1644`-Lineage)
- Kein neuer Merge-Prozess und kein Bypass von `cdb-local-ci`
- Kein Live-/Echtgeld-GO; LR bleibt `NO-GO`; Board-Stage `trade-capable` ist
  kein Live-Go
- Keine Runtime-, Trading-, Risk-, Execution-, produktive DB- oder MCP-Mutation
- Keine privaten Cursor-APIs und kein UI-Scraping als Kernpfad
- Keine Secrets im Klartext in Docs, Issues, Prompts oder Evidence

## 2. Abgrenzung: Agent Control Plane ≠ GitHub Workflow Control Plane

| Fläche | Autorität | Zweck |
| --- | --- | --- |
| **Agent Control Plane** (dieses Dokument) | CDB Governance + Agenten-Skills/Tools | Issue → Route → Contract → Dispatch → Provider-Run → Review → Delivery/Merge-Handoff |
| **GitHub Workflow Control Plane** | `.github/` Automation | CI/Security/Repo-Automation, Workflow-Register, Manifeste, Seal |

Die GitHub Workflow Control Plane bleibt unverändert unter:

- [`.github/CONTROL_PLANE.md`](../../.github/CONTROL_PLANE.md)
- [`docs/governance/GITHUB_CONTROL_PLANE_SEAL.md`](../../docs/governance/GITHUB_CONTROL_PLANE_SEAL.md)
- [`docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md`](../../docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md)
- [`docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`](../../docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md)

Historische Issues `#1640`/`#1644` beschreiben ausschließlich diese Workflow-
Fläche. Sie dürfen weder umbenannt, ersetzt noch mit der ACP vermischt werden.

## 3. Provider-neutrale Architektur

```text
Issue / Human-GO
    │
    ▼
CDB Governance (Policy, Write-Gates, LR/Safety)
    │
    ▼
PR Router (read-only route) ──► existing/new PR lane
    │
    ▼
Agent Execution Contract (handoff payload; schema in #4251)
    │
    ▼
Dispatcher (state machine; #4253) ──► Provider Adapter (#4254+)
    │                                      │
    │                                      ▼
    │                               Cursor (first provider)
    │                                      │
    ▼                                      ▼
Agent Run Evidence ◄────────────── Approval Agent (review only)
    │
    ▼
Delivery Slice in routed PR
    │
    ▼  (separate Merge session)
Completeness Review → Batch Merge Conductor → Final CI / cdb-local-ci → Merge
```

Regeln:

1. **Provider-neutral:** ACP-Verträge sprechen von Provider-Adapter und
   Environments, nicht von Cursor-Dashboard-Klicks.
2. **Cursor first:** Cursor ist der erste Ausführungsprovider; weitere Provider
   dürfen folgen, ohne Authority Matrix oder Lifecycle zu ändern.
3. **Delivery ≠ Merge:** Normale Issue-Sessions enden mit
   `DONE_SLICE_ADDED_TO_BATCH_PR`. Merge bleibt eine getrennte Session unter
   [`docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md`](../../docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md).
4. **Fail-closed:** Fehlender Contract, unsichere Route, ungeeignet Environment
   oder fehlende Evidence stoppt den Lauf; kein implizites Weiterlaufen.

## 4. Authority Matrix

Für jede Komponente gilt genau eine primäre Verantwortung. Spalten:

- **Entscheidet** — setzt verbindliche Auswahl/Policy
- **Darf ausführen** — mutierende oder startende Aktion
- **Darf prüfen** — read-only Bewertung / Gate-Evidence
- **Darf stoppen** — HOLD/BLOCKED/CANCEL auslösen
- **Darf ausdrücklich nicht autorisieren** — harte Negativliste

| Komponente | Entscheidet | Darf ausführen | Darf prüfen | Darf stoppen | Darf ausdrücklich nicht autorisieren |
| --- | --- | --- | --- | --- | --- |
| **CDB Governance** | Policy, Write-Gates, Safety/LR-Grenzen, Canon | Canon-/Policy-Writes nur mit Human-GO und Session-Gates | Governance-Drift, Policy-Verletzungen | STOP bei Safety-/Canon-Verletzung | Live-Go, Echtgeld, produktive DB/MCP-Writes ohne eigenen Gate |
| **PR Router** | Ziel-PR / Branch / Lane / Validation Profile | nichts (read-only) | Kompatibilität, Locks, Inventar | `HOLD_*` bei unsicherer Route | Branch/Worktree/PR-Erstellung, Merge, Status-Publish |
| **Agent Execution Contract** | Handoff-Inhalt und Pflichtfelder (Schema später `#4251`) | nichts | Contract-Vollständigkeit gegen Schema | Fail-closed bei fehlendem/ungültigem Contract | Merge, Live-Go, Provider-Start ohne Dispatcher |
| **Dispatcher** | Run-Start und erlaubte Lifecycle-Übergänge | Provider-Dispatch gemäß Contract + Route + Environment | Preflight (Contract/Route/Env) | HOLD/BLOCKED/FAILED bei Preflight- oder Lauf-Fehler | Merge, Approval ersetzen, Final-CI vortäuschen |
| **Provider Adapter** | Provider-spezifische Aufrufabbildung | Provider-API/CLI/SDK laut öffentlicher Capability | Capability Probe / Drift gegen Registry | STOP wenn Capability fehlt oder Drift kritisch | Private API / UI-Scraping als Kern; Merge; Secrets speichern |
| **Cursor** | nichts in CDB-Authority | Zugewiesene Delivery-Arbeit im Provider-Environment | Provider-lokale Logs/Status an Adapter | Provider-seitiger Abbruch melden | Merge, `cdb-local-ci`, Issue-Close, Live-Go, Governance-Override |
| **Approval Agent** | Review-Verdict (approve / request changes / abstain) im Review-Kontext | Review-Artefakte gemäß Policy | Diff/Evidence gegen Contract und Safety | HOLD bei Policy-/Safety-Findings | Mergefreigabe, Final-CI, Branch Protection, Live-Go |
| **Agent Run Evidence** | nichts | Evidence-Bundle schreiben (Schema später `#4256`) | Vollständigkeit/Integrität des Run-Bundles | BLOCKED bei fehlender Pflicht-Evidence | Brain-Evidence ersetzen; Final-CI vortäuschen; Merge |
| **Final CI / `cdb-local-ci`** | Merge-relevante Commit-Status-Wahrheit auf exaktem Head | Status/Check-Publish nur durch autorisierten Publisher | Fast-CI/Evidence-Bindung an Head SHA | BLOCKED_REQUIRED_STATUS bei missing/red/stale | Slice-Validation als Final-CI zählen; Admin-Bypass |
| **Completeness Review** | `MERGE_CANDIDATE` / Nicht-Kandidat (read-only Aggregat) | nichts | Acht Dimensionen der PR-Completeness | HOLD bei Lücken/Scope-/Wiring-Findings | Merge ausführen; Delivery-Session ersetzen |
| **Batch Merge Conductor** | Freeze, Final-Validation-Orchestrierung, regular squash-merge wenn Capability-Gate erfüllt | Freeze, Rebase/Integrate nach Canon, Merge-Befehl bei Gate | Final-Head-Evidence, Main-Drift | HOLD bei Drift/Capability-/Gate-Fehlern | Delivery-Slice mergen ohne Freeze; `--admin` als Bypass; Fake-Green |

### 4.1 Kurzform Authority

- **CDB entscheidet.** Router weist zu. Contract beschreibt. Dispatcher startet.
  Provider führt aus. Approval prüft. Completeness bewertet Merge-Reife.
  Conductor merged nur nach Final-CI auf exaktem Head.
- **Approval ist Review, keine Mergefreigabe.**
- **Cursor und Delivery-Agenten dürfen nicht mergen.**
- **`cdb-local-ci` bleibt der einzige merge-relevante Required Context**
  (SSOT: [`docs/runbooks/merge_policy_ci_gate.md`](../../docs/runbooks/merge_policy_ci_gate.md)).

## 5. Governed Run Lifecycle

### 5.1 Zustände

| Zustand | Bedeutung |
| --- | --- |
| `PLANNED` | Issue + Human-/Plan-GO vorhanden; noch keine Route gebunden |
| `ROUTED` | PR Router hat sichere Entscheidung geliefert |
| `CONTRACTED` | Execution Contract erfüllt Pflichtfelder |
| `DISPATCHED` | Dispatcher hat Provider-Lauf gestartet |
| `RUNNING` | Provider führt Arbeit aus |
| `AWAITING_APPROVAL` | Review angefordert; Merge noch nicht im Scope |
| `DELIVERED` | Slice im gerouteten PR; Delivery-Session endet |
| `PASS` | Terminal: Delivery-Ziele des Runs erfüllt (nicht gleich Merge) |
| `HOLD` | Terminal/pausierend: wartbar, menschliche/Route-Klärung nötig |
| `BLOCKED` | Terminal: Gate/Capability/Safety blockiert Fortschritt |
| `FAILED` | Terminal: Lauffehler nach Start |
| `CANCELLED` | Terminal: explizit abgebrochen |

### 5.2 Erlaubte Übergänge

```text
PLANNED → ROUTED | HOLD | BLOCKED | CANCELLED
ROUTED → CONTRACTED | HOLD | BLOCKED | CANCELLED
CONTRACTED → DISPATCHED | HOLD | BLOCKED | CANCELLED
DISPATCHED → RUNNING | FAILED | CANCELLED
RUNNING → AWAITING_APPROVAL | DELIVERED | FAILED | HOLD | BLOCKED | CANCELLED
AWAITING_APPROVAL → DELIVERED | HOLD | BLOCKED | CANCELLED
DELIVERED → PASS | HOLD
```

Merge-Pfad (separate Session, nicht Teil des Delivery-Runs):

```text
DELIVERED/PASS (open PR) → Completeness MERGE_CANDIDATE → FROZEN
  → Final CI SUCCESS on exact head → regular squash-merge
```

Ein Delivery-Run darf Completeness/Conductor/Final-CI **referenzieren**, aber
nicht als eigene Autorität starten oder ersetzen.

### 5.3 Terminale Semantik

| Terminal | Semantik |
| --- | --- |
| `PASS` | Governed Delivery-Ziele erreicht; PR/Issue typischerweise noch offen |
| `HOLD` | Fortschritt bewusst gestoppt; Ursache dokumentiert; Retry nach Klärung möglich |
| `BLOCKED` | Gate/Capability/Safety verhindert Fortschritt ohne Scope-/Gate-Änderung |
| `FAILED` | Lauf nach Start fehlgeschlagen; Evidence muss Fehler zeigen |
| `CANCELLED` | Expliziter Abbruch; kein stilles Weiterlaufen |

### 5.4 Fail-closed Pflichtfälle

Sofort `HOLD` oder `BLOCKED` (nie stilles Weiterlaufen), wenn:

- Execution Contract fehlt oder ungültig ist
- PR Router `HOLD_*` oder unsichere Route liefert
- Environment-/Capability-Preflight fehlschlägt
- Pflicht-Evidence fehlt oder Evidence-Arten vermischt/vorgetäuscht werden
- Scope in Runtime/Risk/Live/Secrets driftet
- Private Cursor-Endpunkte oder UI-Scraping als Kernpfad nötig wären

## 6. Evidence-Grenzen

Diese Evidence-Arten sind strikt getrennt. Keine darf die andere vortäuschen.

| Evidence-Art | Was sie belegt | Was sie nicht belegt |
| --- | --- | --- |
| **Brain Evidence** | Kontext-/Trust-Lage aus Context tools/records oder ehrlichem Repo-Fallback | Ausführungserfolg, Final-CI, Merge-Reife |
| **Agent Run Evidence** | Dass ein governed Provider-Lauf startete/endete und welche Artefakte entstand | `cdb-local-ci` SUCCESS; Completeness; Merge-Authority |
| **Targeted Slice Validation** | Eng begrenzte Tests/Checks für den Delivery-Slice | Full Fast-CI / Final-Head-CI |
| **Final CI / `cdb-local-ci`** | Commitgebundene Final-Evidence auf exaktem PR-Head SHA | Slice-Lokalität; Brain-Kontext; Approval-als-Merge |

Regeln:

1. Brain Evidence ist Kontext-Evidence und autorisiert keine Writes.
2. Agent Run Evidence ist Ausführungsevidence und ersetzt keine Final-CI.
3. Targeted Slice Validation ist kein Final-Head-CI.
4. `cdb-local-ci` ist commitgebundene Final-CI-Evidence für Merge-Gates.
5. Approval-Review-Artefakte sind weder Final-CI noch Mergefreigabe.

## 7. Zero-Click und Bootstrap

### 7.1 Normalbetrieb (Zero-Click)

Nach **einmaligem** externem Bootstrap gilt der Normalbetrieb als
**repo-deklarativ**:

- CLI/SDK/öffentliche APIs und repo-versionierte Config/Registry
- Kein wiederholtes Zusammenklicken von Agenten, Triggern, MCPs oder
  Betriebsprofilen im Cursor-Dashboard
- Erwartete spätere Frontdoor (Epic `#4249`, Implementierung außerhalb `#4250`):
  `python -m tools.agent_control plan|apply|dispatch|status|drift`

### 7.2 `MANUAL_BOOTSTRAP_ONLY`

Felder/Capabilities, die öffentlich nicht automatisierbar sind:

1. werden als `MANUAL_BOOTSTRAP_ONLY` inventarisiert,
2. einmalig manuell gesetzt,
3. danach nur noch per **Capability Probe** und **Drift-Meldung** überwacht,
4. nie durch private API oder UI-Scraping „automatisiert“.

### 7.3 Secrets

- Secrets ausschließlich als Referenz oder Secret-Klasse (Store/Environment)
- Keine Klartext-Werte in Canon, Issues, Prompts, Evidence oder Logs
- Provider-API-Keys nur über Secret-Store-/Environment-Referenz

## 8. Truth Order

Bei Konflikten gilt (höher schlägt niedriger):

1. Live GitHub (Issues, PRs, Checks, Branches, Comments)
2. Repo-live Canon/Code
3. Verifizierte Context-/DB-/MCP-Evidence mit Record-Nachweis
4. Canonical Governance (dieses Dokument und Upstream-Policies)
5. Ledger (`CURRENT_STATUS.md` u. a.)
6. Backoffice / Memory

Board-Stage `trade-capable` und Ledger-Einträge erzeugen kein Live-Go.
LR-SSOT bleibt [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).

## 9. Lineage

| Issue | Rolle für ACP |
| --- | --- |
| `#4202`, `#4228` | Gelieferte PR-Routing-/Policy-Grundlage |
| `#4226`, `#4227` | Delivery-/Merge-Skill-Trennung (Lineage; nicht neu erfinden) |
| `#4170` | `cdb-local-ci` / Final-CI-Härtung (Lineage; nicht durch Cursor ersetzen) |
| `#1640`, `#1644` | Historische **GitHub Workflow** Control Plane — nur Abgrenzung |
| `#4249` | Meta-Epic ACP |
| `#4250` | Dieses Canon-Dokument |
| `#4251`+ | Folge-Implementierungen; Schemata/Code außerhalb dieses Docs |

Konflikte mit `#4226`/`#4227`/`#4170` werden nicht durch ACP-Neudefinition
„gelöst“. ACP referenziert ihre gelieferte Semantik und erweitert sie nicht
in Merge- oder Final-CI-Authority.

## 10. Verhältnis zu bestehenden Canon-Flächen

| Fläche | Verhältnis |
| --- | --- |
| [`CDB_AGENT_POLICY.md`](CDB_AGENT_POLICY.md) | Write-Gates, Autonomie-Zonen, Agentenverhalten — ACP ergänzt Orchestrierungs-Authority, ersetzt Policy nicht |
| [`PR_ROUTING_AND_BATCH_MERGE_POLICY.md`](../../docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md) | Delivery/Merge-Trennung und Router — ACP konsumiert, ersetzt nicht |
| [`merge_policy_ci_gate.md`](../../docs/runbooks/merge_policy_ci_gate.md) | Required Final-CI / Capability Merge — ACP konsumiert, ersetzt nicht |
| [`ISSUE_AND_BRANCH_LIFECYCLE.md`](ISSUE_AND_BRANCH_LIFECYCLE.md) | Issue/Branch-Lifecycle — ACP Run-Lifecycle ist orthogonal und ergänzend |
| GitHub Workflow Control Plane | Andere Systemfläche; keine Vermischung |

## 11. Stop-Bedingungen für ACP-Arbeit

STOP und dokumentieren, wenn:

- kein sicherer PR-Route-Entscheid möglich ist
- ein anderer aktiver PR `#4250` bereits implementiert
- Scope Dispatcher-/Provider-/Registry-Code verlangt (andere Child-Issues)
- Merge-Authority oder Live-Go in den Canon rutscht
- private Cursor-Endpunkte oder UI-Scraping erforderlich wären
- verpflichtende Canon-Dateien fehlen oder widersprechen
- ungeklärter Konflikt mit `#4226`, `#4227` oder `#4170` entsteht

## 12. Acceptance Anchor für Folge-Issue `#4251`

Dieses Dokument ist ausreichend als Grundlage für `#4251` (Execution Contract),
wenn `#4251`:

- die Komponenten und Authority-Grenzen hier referenziert,
- Contract-Felder für Route, Scope, Evidence-Erwartungen und Stop-Bedingungen
  spezifiziert,
- **kein** Schema dieses Canons vorwegnehmen muss jenseits der hier genannten
  Lifecycle-/Authority-Namen.

Schema-Details, JSON/YAML-Shapes und Validatoren gehören ausschließlich nach
`#4251` und Folgeslices.
