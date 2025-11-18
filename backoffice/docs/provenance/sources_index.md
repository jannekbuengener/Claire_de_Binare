# Quellen-Index - Wissens-Extraktion Pipeline 2

**Erstellt**: 2025-11-14
**Scope**: Alle relevanten Architektur-, Risk- und Infrastruktur-Dokumente im Repo
**Analyst**: claire-architect

## Primärquellen (Kern-Architektur)

| Dokument | Pfad | Kategorie | Priorität | Extraktionsziel |
|----------|------|-----------|-----------|-----------------|
| ARCHITEKTUR.md | `backoffice/docs/` | Architektur | HOCH | Services, Events, Ports, Infra |
| Risikomanagement-Logik.md | `backoffice/docs/` | Risk-Engine | HOCH | Schutzschichten, Parameter, Logik |
| SERVICE_TEMPLATE.md | `backoffice/docs/` | Entwicklung | HOCH | Service-Struktur, Code-Patterns |
| DEVELOPMENT.md | `backoffice/docs/` | Entwicklung | MITTEL | Workflow, Qualitätsregeln |
| docker-compose.yml | Root | Infrastruktur | HOCH | Container, Networking, Volumes |

## Sekundärquellen (Kontext & Regeln)

| Dokument | Pfad | Kategorie | Priorität | Extraktionsziel |
|----------|------|-----------|-----------|-----------------|
| copilot-instructions.md | `.github/` | Policy | HOCH | Entwicklungs-Leitplanken, MCP-Tools |
| DECISION_LOG.md | `backoffice/docs/` | ADR | MITTEL | Architektur-Entscheidungen, Begründungen |
| README.md | Root | Überblick | NIEDRIG | Projektkontext, Quick-Start |
| TROUBLESHOOTING.md | `backoffice/docs/` | Ops | NIEDRIG | Bekannte Probleme, Lösungen |

## Extraktions-Strategie

### Phase 1: Struktur-Extraktion
- **Ziel**: Kern-Architektur-Elemente (Services, Events, Ports, ENV-Variablen)
- **Quellen**: ARCHITEKTUR.md, docker-compose.yml
- **Agent**: software-jochen
- **Output**: Strukturierte Tabellen in `extracted_knowledge.md`

### Phase 2: Risk-Logik-Extraktion
- **Ziel**: Schutzschichten, Parameter, Entscheidungsregeln
- **Quellen**: Risikomanagement-Logik.md
- **Agent**: software-jochen
- **Output**: Hierarchische Listen mit Prioritäten

### Phase 3: Entwicklungs-Patterns
- **Ziel**: Code-Templates, Qualitätsregeln, Workflows
- **Quellen**: SERVICE_TEMPLATE.md, DEVELOPMENT.md, copilot-instructions.md
- **Agent**: software-jochen
- **Output**: Pattern-Katalog

### Phase 4: Konflikt-Analyse
- **Ziel**: Widersprüche zwischen Dokumenten identifizieren
- **Agent**: agata-van-data
- **Beispiele**:
  - Ports in ARCHITEKTUR.md vs. docker-compose.yml
  - ENV-Variablen in Risikomanagement-Logik.md vs. .env-Referenzen
  - Service-Namen in verschiedenen Dokumenten

### Phase 5: Template-Generierung
- **Ziel**: Abstrahiertes Template für neue Event-Driven Trading Systems
- **Agent**: devops-infrastructure-architect
- **Output**: `project_template.md` mit Platzhaltern und Leitplanken

## Ausschlusskriterien

**Dokumente, die NICHT extrahiert werden:**
- Session-Memos (zeitgebunden, nicht architektur-relevant)
- Test-Reports (laufzeitabhängig)
- Audits (projektspezifisch, nicht abstrakt)
- MCP-Integration-Guides (tool-spezifisch)
- Timelines, Changelogs (historisch)

**Begründung**: Template soll zeitlos und projekt-agnostisch sein.

## Erwartete Konflikte (Hypothesen)

1. **Port-Mappings**: Prometheus in ARCHITEKTUR.md (19090) vs. docker-compose.yml (tatsächliches Mapping)
2. **Service-Namen**: `cdb_core` vs. `signal_engine` in verschiedenen Dokumenten
3. **ENV-Präfixe**: copilot-instructions.md empfiehlt `CDB_*`, bestehende Variablen ohne Präfix
4. **Risk-Parameter Defaults**: Möglicherweise verschiedene Werte in Dokumenten vs. Code

**Validierung**: agata-van-data prüft diese Hypothesen in Phase 4.
