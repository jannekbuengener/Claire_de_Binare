# CDB External Documentation Index

**Stand:** 2026-06-25
**Zweck:** Zentrale Liste externer Dokumentationen für Claire de Binare.
**Canon-Regel:** Eine externe Doku kommt nur in die Liste, wenn sie zu einem aktiven Tool, Service, Agenten oder Runtime-Pfad gehört, eine direkte Repo-Abhängigkeit erklärt, für Onboarding/Debugging/CI/Security/Runtime-Betrieb gebraucht wird oder als Beispiel-/Pattern-Quelle markiert ist.
**Lookup-Trigger:** Agenten in `cdb-external-docs` geladen → hier nachschlagen.

## Prioritäten

| Priority | Bedeutung |
|----------|-----------|
| `required` | Muss vor Arbeit im Bereich geprüft werden |
| `secondary` | Sinnvoll bei aktivem Scope |
| `parked` | Nur bei konkretern Bedarf aktivieren |

---

## KI-Agenten / Coding-Oberflächen

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Repo-/Skill-Flächen | Lookup-Trigger |
|------|----------------|-------------|-----------|---------------------|----------------|
| OpenCode | https://opencode.ai/docs | Agenten-/CLI-/Skill-/MCP-Konfiguration für `.opencode` | required | `.opencode/` | opencode.jsonc, skills, MCP |
| Claude Code | https://code.claude.com/docs/en/overview | Claude-Code-Bootloader, Skills, Agenten-Workflows | required | `.claude/` | CLAUDE.md, Bootloader |
| OpenAI Codex | https://developers.openai.com/codex | Codex CLI/App/IDE, AGENTS.md, Skills, MCP und Workflows | required | `.codex/` | config.toml, agents |
| Cursor | https://cursor.com/docs | Cursor Rules, Subagents, Skills und MCP-Konfiguration | required | `.cursor/` | rules, skills, subagents |
| Gemini API / Google AI | https://ai.google.dev/gemini-api/docs | Gemini-Agentenfläche, API-/Model-Kontext | required | `.gemini/` | settings.json, onboarding |
| GitHub Copilot | https://docs.github.com/en/copilot | Copilot-Review-/Bot-Kommentare | secondary | `.github/` | Review-Threads |
| OpenAI Platform Docs | https://platform.openai.com/docs | Allgemeine OpenAI-API-/Model-/Tooling-Doku | secondary | `.codex/` | API-Integration |

---

## Repo-Control / IDE / SCM

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| GitHub Docs | https://docs.github.com | Issues, PRs, Actions, Security, Repo-Governance | required | Actions, Rulesets, Secrets |
| GitHub CLI | https://cli.github.com/manual | gh-basierte Issue-/PR-/Check-Steuerung | required | CI, PR-Workflow |
| VS Code | https://code.visualstudio.com/docs | Editor-/Workspace-Referenz | secondary | `.vscode/` |
| Conventional Commits | https://www.conventionalcommits.org/en/v1.0.0/ | Commit-/PR-Titel-Format | secondary | CONTRIBUTING.md |

---

## MCP / Context / DB-Brain

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| Model Context Protocol | https://modelcontextprotocol.io/docs | MCP-Server, Tools, Context-Briefings, Agenten-Integration | required | `.mcp.json`, Context-Tools |
| SurrealDB (Hauptdoku) | https://surrealdb.com/docs | Context Intelligence / DB-backed Brain | required | `docs/surrealdb/` |
| SurrealDB Agent Skills | https://github.com/surrealdb/agent-skills | 8 offizielle Skills (surrealql, vector, python, js, cli, surrealkit, performance, functions) | required | `docs/surrealdb/agent-skills-rules-integration-v0.md` |
| SurrealDB Agent Memory | https://github.com/surrealdb/agent-memory | SDK Agent-Memory-Beispiele (Agno, LangChain, LangGraph, Pydantic AI) | secondary | `docs/surrealdb/agent-skills-rules-integration-v0.md` |
| SurrealDB Agent Rules | https://surrealdb.com/docs/integrations/agent-rules | 4 .mdc-Rules (surrealql, vector, python, python-embedded) | required | `docs/surrealdb/agent-skills-rules-integration-v0.md` |

---

## Runtime / Infrastruktur

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| Docker Docs | https://docs.docker.com | Container, Images, Dockerfiles | required | `infrastructure/compose/` |
| Docker Compose | https://docs.docker.com/compose/ | BLUE/RED Compose-Stacks | required | `compose.blue.yml`, `compose.red.yml` |
| Dev Containers | https://containers.dev | Reproduzierbare Entwicklungscontainer | secondary | `.devcontainer/` |
| Redis | https://redis.io/docs/latest/ | Pub/Sub, Streams, Cache, State Transport | required | `services/` |
| PostgreSQL | https://www.postgresql.org/docs/ | Persistenz, Migrationen | required | `infrastructure/database/` |
| Prometheus | https://prometheus.io/docs/ | Metrics, Scraping, Alerting Rules | required | `cdb_prometheus` |
| Grafana | https://grafana.com/docs/ | Dashboards, Monitoring | required | `cdb_grafana` |
| Grafana Loki | https://grafana.com/docs/loki/latest/ | Logging Overlay | secondary | `logging.yml` |
| Promtail | https://grafana.com/docs/loki/latest/send-data/promtail/ | Log Shipping | secondary | `logging.yml` |
| Alertmanager | https://prometheus.io/docs/alerting/latest/alertmanager/ | Alert Routing | secondary | `logging.yml` |
| cAdvisor | https://github.com/google/cadvisor | Container-Metriken | secondary | `cdb_cadvisor` |
| Postgres Exporter | https://github.com/prometheus-community/postgres_exporter | Postgres-Metriken | secondary | `cdb_postgres_exporter` |
| Redis Exporter | https://github.com/oliver006/redis_exporter | Redis-Metriken | secondary | `cdb_redis_exporter` |

---

## Exchange / Marktdaten / Protokolle

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| MEXC Spot V3 API | https://mexcdevelop.github.io/apidocs/spot_v3_en/ | Spot REST/WebSocket/Market-Data | required | `services/ws` |
| MEXC Contract API | https://mexcdevelop.github.io/apidocs/contract_v1_en/ | Contract/Futures | secondary | `services/execution/` |
| Protocol Buffers | https://protobuf.dev/ | MEXC WebSocket-Protobuf-Decoder | required | `services/ws/mexc_proto_gen/` |
| websockets Python | https://websockets.readthedocs.io/en/stable/ | Python WebSocket Client | required | `services/ws/` |

---

## Python / CI / Dev-Qualität

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| Python | https://docs.python.org/3/ | Primäre Runtime- und Tooling-Sprache | required | `pyproject.toml` |
| pytest | https://docs.pytest.org/en/stable/ | Unit-/Integration-/Smoke-/E2E-Tests | required | `tests/` |
| Ruff | https://docs.astral.sh/ruff/ | Linting (CI-required) | required | `pyproject.toml` |
| mypy | https://mypy.readthedocs.io/en/stable/ | Type Checking | secondary | `requirements-dev.txt` |
| Black | https://black.readthedocs.io/en/stable/ | Formatter | secondary | `pyproject.toml` |
| pre-commit | https://pre-commit.com/ | Hooks für Secrets, Commits, Lint | required | `.pre-commit-config.yaml` |
| Flask | https://flask.palletsprojects.com/en/stable/ | HTTP Health/Status/Metrics | required | `service.py` |
| Werkzeug | https://werkzeug.palletsprojects.com/en/stable/ | Flask-HTTP-Unterbau | secondary | `requirements*.txt` |
| psycopg2 | https://www.psycopg.org/docs/ | PostgreSQL Client | required | `requirements*.txt` |
| redis-py | https://redis.readthedocs.io/en/stable/ | Redis Client | required | `requirements*.txt` |
| aiohttp | https://docs.aiohttp.org/en/stable/ | Async HTTP Dependency | secondary | `requirements*.txt` |
| requests | https://requests.readthedocs.io/en/latest/ | REST/HTTP Client | secondary | `requirements*.txt` |
| jsonschema | https://python-jsonschema.readthedocs.io/en/stable/ | Contract-/Schema-Validation | secondary | `services/validation/` |
| PyYAML | https://pyyaml.org/wiki/PyYAMLDocumentation | YAML Parsing | parked | `requirements-dev.txt` |

---

## Security / Supply Chain

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| Gitleaks | https://gitleaks.io/ | Secret Scanning | required | `gitleaks.toml` |
| Bandit | https://bandit.readthedocs.io/en/latest/ | Python Security Linting | secondary | `requirements-dev.txt` |
| pip-audit | https://pypa.github.io/pip-audit/ | Dependency Vulnerability Audit | secondary | `requirements-dev.txt` |
| Trivy | https://trivy.dev/docs/ | Container/Supply-Chain Scan | secondary | `.trivyignore` |

---

## Geparkt (nur bei konkretem Scope)

| Name | Offizielle Docs | CDB-Nutzung | Priorität | Lookup-Trigger |
|------|----------------|-------------|-----------|----------------|
| Kubernetes | https://kubernetes.io/docs/ | Keine aktive Deploy-Fläche; Docker Compose ist Canon | parked | `knowledge/decisions/K8S_BUDGET_DECISION.md` |
| Binance API | https://developers.binance.com/docs | Nur bei aktivem Exchange-Scope | parked | Exchange-Erweiterung |
| FastAPI | https://fastapi.tiangolo.com/ | Aktuell kein Hauptpfad (Services nutzen Flask) | parked | Service-Neubau |
| SQLAlchemy | https://docs.sqlalchemy.org/ | Nur bei ORM-/DB-Abstraktions-Scope | parked | DB-Refactoring |
| Alembic | https://alembic.sqlalchemy.org/en/latest/ | Nur bei Migration-Tooling-Scope | parked | DB-Migration |
| Node.js | https://nodejs.org/docs/latest/api/ | Lokales Tooling, CDB-Core sekundär | parked | CLI-Tooling |
| npm | https://docs.npmjs.com/ | Nur bei Node-/Package-Scope | parked | Node-Dependency |

## Verwendung

Dieses Verzeichnis wird vom Skill `cdb-external-docs` referenziert.
Agenten laden diesen Skill bei Bedarf und schlagen hier nach, welche externe Doku für ein konkretes Problem relevant ist.
