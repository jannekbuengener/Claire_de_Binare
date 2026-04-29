# CDB Context Intelligence System — Roadmap & Issue Map

**Status**: Draft (Wave 7)
**Authority**: Issue #2036 / Epic #1976
**Context**: Part of the Landing Foundation (#2034)

## 1. Zweck
Dieses Dokument dient als kanonische Orientierung für den Rollout des CDB SurrealDB Context Intelligence Systems (CIS). Es verbindet die strategischen Roadmap-Blöcke aus Epic #1976 mit den operativen GitHub-Issues und Wellen, um einen konsistenten Handoff zwischen Agenten zu ermöglichen.

## 2. Scope und Nicht-Ziele
- **Scope**: Dokumentation der Wellen 1 bis 14 (Design, Landing, Implementierung).
- **Nicht-Ziele**:
    - Dieses Dokument ist kein automatisches "Go" für Implementierungswellen.
    - Es ersetzt nicht die Live-Wahrheit in GitHub.
    - Es autorisiert keine Runtime-Änderungen.

## 3. Verhältnis zu #1976, #2034 und #2035
- **Epic #1976**: Definierte das Gesamtbild und die 20 Roadmap-Blöcke.
- **Wave-7 Landing #2034**: Der aktuelle operative Slice, um CIS ins Working Repo zu bringen.
- **Architektur #2035**: Definierte die Systemgrenzen und Komponenten.
- **Roadmap #2036 (Dieses Dokument)**: Schließt die Lücke zwischen Vision und Issue-Tracking.

## 4. Roadmap-Übersicht

Das Projekt ist in drei Hauptphasen unterteilt:
1.  **Design-Wellen (1–6)**: Theoretische Fundamente, Ontologie, Schema-Entwürfe und Logikmodelle.
2.  **Landing Foundation (Welle 7)**: Initialer Footprint im Repository (Dokumentation, Roadmap, Validation-Scaffold).
3.  **Implementierungs-Wellen (8–14)**: Schrittweiser Aufbau des Indexers, der SurrealDB-Integration und der Agent-Tools.

## 5. Phasen und Wellen

### Phase 1: Design & Spezifikation (Wellen 1–6)
| Welle | Issue-Range | Fokus |
| :--- | :--- | :--- |
| **Welle 1** | #1977–#1984 | Zielbild, Ontologie, Kernschema, Relation Vocabulary. |
| **Welle 2** | #1985–#1993 | Repo-/Doku-Ingestion Foundation. |
| **Welle 3** | #1994–#2003 | Code Symbol Graph & Dependency Foundation. |
| **Welle 4** | #2004–#2013 | Evidence Fabric, Decision Graph & Controlled Memory. |
| **Welle 5** | #2014–#2023 | Hybrid Retrieval, Agent Briefings & Impact Radar Contracts. |
| **Welle 6** | #2024–#2033 | Contradiction Detection, Scope Drift & Self-Explanation Models. |

### Phase 2: Landing Foundation (Welle 7)
| Welle | Issue-Range | Fokus |
| :--- | :--- | :--- |
| **Welle 7** | #2034–#2043 | **Aktueller Fokus.** Landen der Architektur, Roadmap und Validierung im Repo. |

### Phase 3: Implementierung (Wellen 8–14)
| Welle | Issue-Range | Fokus |
| :--- | :--- | :--- |
| **Welle 8** | #2044–#2054 | Context Indexer Scaffold, Hashing, Export Pipeline. |
| **Welle 9** | #2055–#2066 | Symbol-/Graph-Extraktion (Python AST). |
| **Welle 10** | #2067–#2078 | SurrealDB Import, Reconcile & Apply Pipeline. |
| **Welle 11** | #2079–#2090 | Context Query CLI & Retrieval Foundation. |
| **Welle 12** | #2091–#2102 | MCP Bridge & Context Tools (Read-only). |
| **Welle 13** | #2103–#2114 | Agent Briefing Engine & Impact Radar v1. |
| **Welle 14** | #2115–#2128 | Evidence, Decision & Memory Retrieval v1. |

### Phase 4: Agent Intelligence Layer (Wellen 15–16)
| Welle | Issue-Range | Fokus |
| :--- | :--- | :--- |
| **Welle 15** | #2145–#2152 | Contradiction Detection Runtime v1. |
| **Welle 16** | #2153–#2161 | Stale Knowledge Runtime & Refresh Planning. |

### Phase 5: Governance Intelligence Runtime (Wellen 17–21)
| Welle | Issue-Range | Fokus |
| :--- | :--- | :--- |
| **Welle 17** | #2162–#2169 | Scope Drift Firewall Runtime v1. |
| **Welle 18** | #2170–#2178 | Knowledge Quality Scoring & Architect Signals. |
| **Welle 19** | #2179–#2187 | Visual Control Room & Reporting Layer. |
| **Welle 20** | #2188–#2196 | Self-Explanation & Agent OS Readiness. |
| **Welle 21** | #2197–#2205 | **Aktueller Fokus.** Cross-cutting Hardening, Search, CI & Operations. |

## 6. Roadmap-Blöcke (0–20)
Gemäß Epic #1976 werden folgende Blöcke adressiert:
0. Projektanker & Grenzen (#1976, #2035)
1. SurrealDB Fundament
2. CDB Operating Ontology (#2038)
3. Kernschema (#2037)
4. Repo-/Doku-Ingestion (#2047)
5. Code Symbol Graph (#2057)
... (fortlaufend bis Block 20: Agent Operating System #2032)

## 7. Issue-Mapping (Auszug wichtige Meilensteine)
| Issue | Titel | Welle | Rolle |
| :--- | :--- | :--- | :--- |
| #1976 | Epic: CDB CIS | - | Parent Anchor |
| #2035 | CIS Architecture | 7 | Canonical Boundaries |
| #2036 | CIS Roadmap | 7 | Issue Map (Dieses Doc) |
| #2037 | SurrealQL Schema | 7 | Initial Data Model Draft |
| #2038 | CDB Ontology | 7 | Semantic Seed |
| #2040 | Agent Handoff | 7 | Manual for Implementers |
| #2045 | Indexer Scaffold | 8 | Start of Implementation |

## 8. Abhängigkeitsmodell
- **Wellen-Sequenz**: Die Wellen 1–6 sind konzeptionelle Vorraussetzungen für Welle 7.
- **Implementierungs-Gate**: Wellen 8–14 bauen streng sequenziell aufeinander auf (Indexer -> Extraktion -> Import -> Query -> Tooling).
- **PR-Slicing**: Implementierungen erfolgen in kleinen, validierbaren PRs gemäß #2042.

## 9. Guardrails
- **Kein Runtime-Umbau**: CIS beeinflusst keine bestehende Trading-Logik.
- **Keine produktive SurrealDB-Aktivierung**: In Welle 7 erfolgt kein Start von Datenbank-Instanzen.
- **Kein Live-/Echtgeld-Go**: CIS-Fortschritt ist orthogonal zur Live-Readiness.
- **GitHub Live Authority**: Im Zweifelsfall gewinnt der aktuelle Status in den GitHub-Issues gegenüber diesem Dokument.
- **Ledger-Only**: `CURRENT_STATUS.md` bleibt der technische Ledger für Commits/PRs.

## 10. Validierungs-Checkliste
- [ ] Sind alle Issues #1976–#2043 korrekt referenziert?
- [ ] Ist der Übergang von Design zu Implementierung (Welle 7->8) klar markiert?
- [ ] Wurden die Guardrails explizit aufgenommen?
- [ ] Ist das Dokument für einen neuen Agenten ohne Chatverlauf verständlich?

## Provenance / Quellen
- **Epic**: #1976
- **Parent**: #2034
- **Foundation**: #2035, PR #2130
- **Docs**: `docs/surrealdb/context-intelligence-system.md`
