# Core System Eventflows — Onboarding Pack

## Status

Docs-only onboarding artifact. Visual orientation — not authoritative.

Status: docs-only, LR remains NO-GO, kein Live-Go, kein Echtgeld-Go.

## Parent / Issue Refs

- Parent: [#3253 Core-System Eventflow Map Pack](https://github.com/jannekbuengener/Claire_de_Binare/issues/3253)
- Child Issues: #3254, #3255, #3256, #3257, #3258, #3259, #3260, #3261
- Glossary Issue: [#3262 Extend CDB Glossary](https://github.com/jannekbuengener/Claire_de_Binare/issues/3262)
- Glossary Dependency: [#3247 V2 Glossary](https://github.com/jannekbuengener/Claire_de_Binare/issues/3247)

## Ziel des Packs

Dieses Pack visualisiert die Kernsystem-Flüsse von Claire de Binare: Runtime Eventbus,
BLUE/RED Topology, Signal Decision, Risk Gate, Execution/Paper Feedback, Persistence/Audit,
ARVP Replay Validation und den Profitability Candidate Lifecycle.

Neue Developer und Agents sollen den echten Systemfluss verstehen, bevor sie an
Runtime-, Strategy-, Risk- oder Execution-Code arbeiten.

## Wann dieses Pack lesen

- Du bist neu im Repo und hast die Start-Pfade in
  [`DEVELOPER_VISUAL_START_HERE.md`](../DEVELOPER_VISUAL_START_HERE.md) gelesen.
- Du planst Arbeiten an einem Runtime-Service, der Strategie, Risk oder Execution betrifft.
- Du möchtest den Datenfluss zwischen den CDB-Komponenten verstehen.
- Du bereitest einen Agenten-Prompt für systemnahe Arbeiten vor.

## Reihenfolge der Flow-Dokumente

Die Dokumente bauen inhaltlich aufeinander auf. Lies sie in dieser Reihenfolge:

| # | Flow | Kernfrage |
|---|------|-----------|
| 1 | [Core Runtime Eventflow](core_runtime_eventflow.md) | Wie fliessen Daten durch das System? |
| 2 | [BLUE/RED Runtime Topology](blue_red_runtime_topology.md) | Welche Services gehören zu welchem Stack? |
| 3 | [Signal Decision Flow](signal_decision_flow.md) | Wie entsteht ein Signal? |
| 4 | [Risk Gate Flow](risk_gate_flow.md) | Wie wird ein Signal zur Order? |
| 5 | [Execution, Paper/Mock and Order Result Feedback](execution_paper_order_result_flow.md) | Wie wird eine Order ausgeführt? |
| 6 | [Persistence and Audit Chain](persistence_audit_chain_flow.md) | Wie werden Events persistiert? |
| 7 | [ARVP Replay Validation Flow](arvp_replay_validation_flow.md) | Wie wird offline validiert? |
| 8 | [Profitability Candidate Lifecycle](profitability_candidate_lifecycle_flow.md) | Wie wird aus einer Idee ein Kandidat? |

## Flow-Übersicht

| Flow | Issue | Datei | Kernfrage |
|------|-------|-------|-----------|
| Core Runtime Eventflow | [#3254](https://github.com/jannekbuengener/Claire_de_Binare/issues/3254) | [`core_runtime_eventflow.md`](core_runtime_eventflow.md) | Wie fliessen Daten durch das System? |
| BLUE/RED Topology | [#3255](https://github.com/jannekbuengener/Claire_de_Binare/issues/3255) | [`blue_red_runtime_topology.md`](blue_red_runtime_topology.md) | Welche Services gehören zu welchem Stack? |
| Signal Decision | [#3256](https://github.com/jannekbuengener/Claire_de_Binare/issues/3256) | [`signal_decision_flow.md`](signal_decision_flow.md) | Wie entsteht ein Signal? |
| Risk Gate | [#3257](https://github.com/jannekbuengener/Claire_de_Binare/issues/3257) | [`risk_gate_flow.md`](risk_gate_flow.md) | Wie wird ein Signal zur Order? |
| Execution/Paper | [#3258](https://github.com/jannekbuengener/Claire_de_Binare/issues/3258) | [`execution_paper_order_result_flow.md`](execution_paper_order_result_flow.md) | Wie wird eine Order ausgeführt? |
| Persistence/Audit | [#3259](https://github.com/jannekbuengener/Claire_de_Binare/issues/3259) | [`persistence_audit_chain_flow.md`](persistence_audit_chain_flow.md) | Wie werden Events persistiert? |
| ARVP Replay | [#3260](https://github.com/jannekbuengener/Claire_de_Binare/issues/3260) | [`arvp_replay_validation_flow.md`](arvp_replay_validation_flow.md) | Wie wird offline validiert? |
| Candidate Lifecycle | [#3261](https://github.com/jannekbuengener/Claire_de_Binare/issues/3261) | [`profitability_candidate_lifecycle_flow.md`](profitability_candidate_lifecycle_flow.md) | Wie wird aus einer Idee ein Kandidat? |

## Safety Summary

- **Docs-only.** Keine Runtime-, Service-, DB-, Risk-, Execution-, Allocation- oder LR-Änderung.
- **LR bleibt NO-GO.** Board stage `trade-capable` ist kein Live-Go. Kein Echtgeld-Go.
- **Kein Code.** Diese Dokumente sind reine Markdown/Mermaid-Visualisierungen.
- **Orientierung, nicht Authority.** Die kanonischen Quellen bleiben die im Bootloader
  genannten Dateien und der GitHub Live State.
- **Keine automatische Promotion.** Keine Ableitung von Live-Berechtigung aus Visuals.

## Quellenliste

- [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)
- [`services/README.md`](../../services/README.md)
- [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)
- [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)
- [`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`](../DEVELOPER_VISUAL_START_HERE.md)

## Glossary

Die Begriffe in diesen Flow-Dokumenten werden im kanonischen
[CDB Glossary](../cdb_glossary.md) definiert. Es vereint die allgemeine CDB-Terminologie
aus [#3247](https://github.com/jannekbuengener/Claire_de_Binare/issues/3247)
und die Core-System-Flow-Begriffe aus
[#3262](https://github.com/jannekbuengener/Claire_de_Binare/issues/3262).

## Hinweis: Board trade-capable ist kein Live-Go

Board stage `trade-capable` ([`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md))
ist ein betrieblicher Fokus, keine Live-Freigabe. Das LR-System
([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md))
bleibt die alleinige SSOT für Echtgeld Go/No-Go.
