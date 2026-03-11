---
relations:
  role: doc
  domain: governance
  upstream:
    - knowledge/governance/CDB_REPO_STRUCTURE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_PSM_POLICY.md
  downstream: []
  status: canonical
  tags: [repository, guidelines, working_repo]
---
# CDB_REPO_GUIDELINES
**Working Repo Guidelines (Canonical)**

Gilt für: Working Repo (*Execution Only*)  
Gilt nicht für: Docs Hub (knowledge/governance/Knowledge/Agents)

---

## 1. Struktur & Module

- `/core`  
  shared domain models, typed config loaders, utilities; keine service-spezifische Logik

- `/services`  
  stateless runtime components (execution, risk, signal, psm, db_writer, …)  
  pro Service: Modul, Config, Dockerfile, requirements

- `/infrastructure`  
  deployment scaffolding: compose, k8s, monitoring, database schema/migrations

- `/tests`  
  `unit/`, `integration/`, `replay/` aligned nach Services

- `/governance`  
  existiert **nicht** im Working Repo (Canon liegt im Docs Hub)

---

## 2. Build & Test Commands (Working Repo)

- `make test`  
  führt `make test-unit` und `make test-integration` aus

- `make test-unit`  
  `pytest -v -m unit`

- `make test-integration`  
  `pytest -v -m "integration and not e2e and not local_only"`

- `make test-e2e` / `make test-local*`  
  nur lokal, kontrolliert, setzt `docker compose up -d` voraus

- `make docker-up` / `make docker-down` / `make docker-health`  
  Compose Stack steuern & prüfen

---

## 3. Coding Style & Determinismus

- Python: `snake_case` (functions/vars), `CamelCase` (classes)
- 4 spaces indent
- Helpers bevorzugt pure/deterministisch
- keine versteckte Randomness/Timestamps ohne explizite Config (`seed`, `timestamp`)
- Config via env/ConfigMaps/Secrets; keine Hardcoded Secrets

---

## 4. Testing Guidelines

- `pytest` marker: `unit`, `integration`, `e2e`, `local_only`, `slow`, …
- Tests: `test_<area>.py`, Struktur spiegelt Services
- Replay-Tests unter `/tests/replay/` sind Pflicht (PSM-Policy)
- Vor Merges: `make test` (oder gezielt) + ggf. `make test-coverage`

---

## 5. Commits & PRs

- Conventional style: `type(scope): short description`
- PR muss enthalten:
  - was geändert
  - welche Tests
  - Risiken / Rollback-Hinweis
  - Logs/Screenshots nur wenn nötig

---

## Abschluss

Diese Guidelines sichern Konsistenz und Determinismus im Working Repo.  
Canon lebt im Docs Hub.
