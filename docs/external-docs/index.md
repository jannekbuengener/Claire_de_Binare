# CDB External Documentation Index

**Stand:** 2026-10-20  
**Zweck:** Zentrale repo-lokale Liste externer technischer Referenzen für Claire de Binare.  
**Contract:** <https://github.com/jannekbuengener/agent-workforce/blob/main/contracts/EXTERNAL_REFERENCE_CONTRACT.md>  
**Canon-Regel:** Eine externe Doku kommt nur in die Liste, wenn sie zu einem aktiven Tool, Service, Agenten oder Runtime-Pfad gehört, eine direkte Repo-Abhängigkeit erklärt, für Onboarding/Debugging/CI/Security/Runtime-Betrieb gebraucht wird oder als Beispiel-/Pattern-Quelle markiert ist.  
**Lookup-Trigger:** Agenten in `cdb-external-docs` geladen → hier nur die für den aktuellen Task relevanten Einträge nachschlagen.

Diese Liste beschreibt **Referenz-Relevanz**, nicht CDB-Repo-Wahrheit. GitHub-/Repo-Live-State, lokaler Canon, Source/Config/CI und Dependency-Manifeste bleiben für den tatsächlichen CDB-Zustand autoritativ.

## Prioritäten

| Priority | Bedeutung |
|---|---|
| `P0` | Aktive Kernreferenz; für den jeweiligen aktuellen CDB-Pfad zentral und durch ein Repo-Signal belegt. |
| `P1` | Aktive sekundäre Referenz; bei passendem Scope relevant und durch ein Repo-Signal belegt. |
| `P2` | Geparkt/reference-only; erst bei konkretem Scope aktivieren, niemals als Beleg für aktive Implementierung lesen. |

Priorität beschreibt **CDB-Relevanz**, nicht Source Authority.

## Source Type und Authority

Die bestehende Spalte `Offizielle Docs` ist der portable Upstream-/Referenz-Link. Die Quelle wird nach dem Agent-Workforce-Contract semantisch so eingeordnet:

1. `official_spec` / `OFFICIAL_SPEC` — veröffentlichte Spezifikation des zuständigen Standards/Projekts;
2. `official_docs` / `OFFICIAL_DOCS` — offizielle Produkt-, Plattform-, Sprach- oder API-Dokumentation;
3. `upstream_project_docs` / `UPSTREAM_PROJECT_DOCS` — vom Upstream-Projekt gepflegte Repository-/Projekt-Dokumentation;
4. `upstream_issues_releases` / `UPSTREAM_ISSUES_RELEASES` — Upstream-Issues, Releases, Changelogs und Maintainer-Evidence;
5. `established_technical_knowledge` / `ESTABLISHED_TECHNICAL_KNOWLEDGE`;
6. `community` / `COMMUNITY`;
7. `example_discovery` / `EXAMPLE_DISCOVERY`.

Die Einträge unten verlinken überwiegend `OFFICIAL_DOCS`; GitHub-Projekt-Repositories wie cAdvisor oder Exporter sind `UPSTREAM_PROJECT_DOCS`. Community-/Example-Quellen dürfen Discovery unterstützen, aber weder aktuelle offizielle/upstream Evidence noch CDB-Live-State überschreiben.

---

## KI-Agenten / Coding-Oberflächen

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Repo-/Skill-Flächen | Lookup-Trigger |
|---|---|---|---|---|---|
| OpenCode | https://opencode.ai/docs | Agenten-/CLI-/Skill-/MCP-Konfiguration für `.opencode` | `P0` | `.opencode/` | opencode.jsonc, skills, MCP |
| Claude Code | https://code.claude.com/docs/en/overview | Claude-Code-Bootloader, Skills, Agenten-Workflows | `P0` | `.claude/` | CLAUDE.md, Bootloader |
| OpenAI Codex | https://developers.openai.com/codex | Codex CLI/App/IDE, AGENTS.md, Skills, MCP und Workflows | `P0` | `.codex/` | config.toml, agents |
| Cursor | https://cursor.com/docs | Cursor Rules, Subagents, Skills und MCP-Konfiguration | `P0` | `.cursor/` | rules, skills, subagents |
| Google Jules API | https://developers.google.com/jules/api | Jules als CDB-Agent-Control-Plane-Provider; REST-v1alpha-Session/Plan/Activities/Follow-up | `P0` | `tools/agent_control/providers/jules_api.py`, `cdb-jules-dispatch` | issue #4461, Jules provider lifecycle |
| Gemini API / Google AI | https://ai.google.dev/gemini-api/docs | Gemini-Agentenfläche, API-/Model-Kontext | `P0` | `.gemini/` | settings.json, onboarding |
| GitHub Copilot | https://docs.github.com/en/copilot | Copilot-Review-/Bot-Kommentare | `P1` | `.github/` | Review-Threads |
| OpenAI Platform Docs | https://platform.openai.com/docs | Allgemeine OpenAI-API-/Model-/Tooling-Doku | `P1` | `.codex/` | API-Integration |

---

## Repo-Control / IDE / SCM

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| GitHub Docs | https://docs.github.com | Issues, PRs, Actions, Security, Repo-Governance | `P0` | Actions, Rulesets, Secrets |
| GitHub CLI | https://cli.github.com/manual | gh-basierte Issue-/PR-/Check-Steuerung | `P0` | CI, PR-Workflow |
| VS Code | https://code.visualstudio.com/docs | Editor-/Workspace-Referenz | `P1` | `.vscode/` |
| Conventional Commits | https://www.conventionalcommits.org/en/v1.0.0/ | Commit-/PR-Titel-Format | `P1` | CONTRIBUTING.md |

---

## MCP / Context / DB-Brain

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| Model Context Protocol | https://modelcontextprotocol.io/docs | MCP-Server, Tools, Context-Briefings, Agenten-Integration | `P0` | `.mcp.json`, Context-Tools |
| SurrealDB (Hauptdoku) | https://surrealdb.com/docs | Context Intelligence / DB-backed Brain | `P0` | `docs/surrealdb/` |
| SurrealDB Agent Skills | https://github.com/surrealdb/agent-skills | 8 offizielle Skills (surrealql, vector, python, js, cli, surrealkit, performance, functions) | `P0` | `docs/surrealdb/agent-skills-rules-integration-v0.md` |
| SurrealDB Agent Memory | https://github.com/surrealdb/agent-memory | SDK Agent-Memory-Beispiele (Agno, LangChain, LangGraph, Pydantic AI) | `P1` | `docs/surrealdb/agent-skills-rules-integration-v0.md` |
| SurrealDB Agent Rules | https://surrealdb.com/docs/integrations/agent-rules | 4 .mdc-Rules (surrealql, vector, python, python-embedded) | `P0` | `docs/surrealdb/agent-skills-rules-integration-v0.md` |

---

## Runtime / Infrastruktur

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| Docker Docs | https://docs.docker.com | Container, Images, Dockerfiles | `P0` | `infrastructure/compose/` |
| Docker Compose | https://docs.docker.com/compose/ | BLUE/RED Compose-Stacks | `P0` | `compose.blue.yml`, `compose.red.yml` |
| Dev Containers | https://containers.dev | Reproduzierbare Entwicklungscontainer | `P1` | `.devcontainer/` |
| Redis | https://redis.io/docs/latest/ | Pub/Sub, Streams, Cache, State Transport | `P0` | `services/` |
| PostgreSQL | https://www.postgresql.org/docs/ | Persistenz, Migrationen | `P0` | `infrastructure/database/` |
| Prometheus | https://prometheus.io/docs/ | Metrics, Scraping, Alerting Rules | `P0` | `cdb_prometheus` |
| Grafana | https://grafana.com/docs/ | Dashboards, Monitoring | `P0` | `cdb_grafana` |
| Grafana Loki | https://grafana.com/docs/loki/latest/ | Logging Overlay | `P1` | `logging.yml` |
| Promtail | https://grafana.com/docs/loki/latest/send-data/promtail/ | Log Shipping | `P1` | `logging.yml` |
| Alertmanager | https://prometheus.io/docs/alerting/latest/alertmanager/ | Alert Routing | `P1` | `logging.yml` |
| cAdvisor | https://github.com/google/cadvisor | Container-Metriken | `P1` | `cdb_cadvisor` |
| Postgres Exporter | https://github.com/prometheus-community/postgres_exporter | Postgres-Metriken | `P1` | `cdb_postgres_exporter` |
| Redis Exporter | https://github.com/oliver006/redis_exporter | Redis-Metriken | `P1` | `cdb_redis_exporter` |

---

## Exchange / Marktdaten / Protokolle

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| MEXC Spot V3 API | https://mexcdevelop.github.io/apidocs/spot_v3_en/ | Spot REST/WebSocket/Market-Data | `P0` | `services/ws` |
| MEXC Contract API | https://mexcdevelop.github.io/apidocs/contract_v1_en/ | Contract/Futures | `P1` | `services/execution/` |
| Protocol Buffers | https://protobuf.dev/ | MEXC WebSocket-Protobuf-Decoder | `P0` | `services/ws/mexc_proto_gen/` |
| websockets Python | https://websockets.readthedocs.io/en/stable/ | Python WebSocket Client | `P0` | `services/ws/` |

---

## Python / CI / Dev-Qualität

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| Python | https://docs.python.org/3/ | Primäre Runtime- und Tooling-Sprache | `P0` | `pyproject.toml` |
| pytest | https://docs.pytest.org/en/stable/ | Unit-/Integration-/Smoke-/E2E-Tests | `P0` | `tests/` |
| Ruff | https://docs.astral.sh/ruff/ | Linting (CI-required) | `P0` | `pyproject.toml` |
| mypy | https://mypy.readthedocs.io/en/stable/ | Type Checking | `P1` | `requirements-dev.txt` |
| Black | https://black.readthedocs.io/en/stable/ | Formatter | `P1` | `pyproject.toml` |
| pre-commit | https://pre-commit.com/ | Hooks für Secrets, Commits, Lint | `P0` | `.pre-commit-config.yaml` |
| Flask | https://flask.palletsprojects.com/en/stable/ | HTTP Health/Status/Metrics | `P0` | `service.py` |
| Werkzeug | https://werkzeug.palletsprojects.com/en/stable/ | Flask-HTTP-Unterbau | `P1` | `requirements*.txt` |
| psycopg2 | https://www.psycopg.org/docs/ | PostgreSQL Client | `P0` | `requirements*.txt` |
| redis-py | https://redis.readthedocs.io/en/stable/ | Redis Client | `P0` | `requirements*.txt` |
| aiohttp | https://docs.aiohttp.org/en/stable/ | Async HTTP Dependency | `P1` | `requirements*.txt` |
| requests | https://requests.readthedocs.io/en/latest/ | REST/HTTP Client | `P1` | `requirements*.txt` |
| jsonschema | https://python-jsonschema.readthedocs.io/en/stable/ | Contract-/Schema-Validation | `P1` | `services/validation/` |
| PyYAML | https://pyyaml.org/wiki/PyYAMLDocumentation | YAML Parsing | `P2` | `requirements-dev.txt`; nur bei YAML-/Governance-Scope laden |

---

## Security / Supply Chain

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| Gitleaks | https://gitleaks.io/ | Secret Scanning | `P0` | `gitleaks.toml` |
| Bandit | https://bandit.readthedocs.io/en/latest/ | Python Security Linting | `P1` | `requirements-dev.txt` |
| pip-audit | https://pypa.github.io/pip-audit/ | Dependency Vulnerability Audit | `P1` | `requirements-dev.txt` |
| Trivy | https://trivy.dev/docs/ | Container/Supply-Chain Scan | `P1` | `.trivyignore` |

---

## Geparkt — nur bei konkretem Scope

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|---|---|---|---|---|
| Kubernetes | https://kubernetes.io/docs/ | Keine aktive Deploy-Fläche; Docker Compose ist Canon | `P2` | `knowledge/decisions/K8S_BUDGET_DECISION.md` |
| Binance API | https://developers.binance.com/docs | Nur bei aktivem Exchange-Scope | `P2` | Exchange-Erweiterung |
| FastAPI | https://fastapi.tiangolo.com/ | Aktuell kein Hauptpfad (Services nutzen Flask) | `P2` | Service-Neubau |
| SQLAlchemy | https://docs.sqlalchemy.org/ | Nur bei ORM-/DB-Abstraktions-Scope | `P2` | DB-Refactoring |
| Alembic | https://alembic.sqlalchemy.org/en/latest/ | Nur bei Migration-Tooling-Scope | `P2` | DB-Migration |
| Node.js | https://nodejs.org/docs/latest/api/ | Lokales Tooling, CDB-Core sekundär | `P2` | CLI-Tooling |
| npm | https://docs.npmjs.com/ | Nur bei Node-/Package-Scope | `P2` | Node-Dependency |

## Verwendung

Dieses Verzeichnis wird vom Skill `cdb-external-docs` referenziert. Agenten laden diesen Skill nur bei Bedarf und wählen anschließend ausschließlich Referenzen, deren Kategorie/Repo-Signal/Lookup-Trigger zum aktuellen Task passen.

`P2` bleibt geparkt und darf ohne aktivierenden Scope nicht als heutige CDB-Technologie oder Implementierungsannahme gelesen werden. Externe Referenzen autorisieren keine Dependency-, Runtime-, Control-Plane-, Trading- oder Live-Readiness-Mutation.