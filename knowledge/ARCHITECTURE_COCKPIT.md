# 🚀 Architektur-Cockpit: Claire de Binare

**Zweck:** Arbeits-Startseite (fuer dich + Agenten). Von hier aus findest du Design, Policies und Implementierung in diesem Repo in <60 Sekunden.

## Link-Konvention
- **Lokale Doku**: relative Links innerhalb dieses Repos.
- **Working Repo Code**: GitHub-Link mit Branch-Placeholder:  
  `https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/<path>`

---

## 🗺️ Systemkarte (20-Sekunden-Überblick)

```mermaid
graph LR
  S[Signal Service] -->|Topic: signals| R[Risk Service]
  R -->|Topic: orders| X[Execution Service]
  X -->|Topic: order_results| W[DB Writer]
  X -->|Stream: order_results (XADD)| W
  W -->|Tables: orders, trades| P[(Postgres)]
  R <-->|Topic: order_results| X

  R -->|Stream: stream.bot_shutdown| X
```

---

## ⚙️ Kernkomponenten: Design ↔️ Code ↔️ Contracts
| Komponente | Zweck | Contracts (Topics/Streams/DB) | Design (Docs) | Code (Working Repo) |
| :--- | :--- | :--- | :--- | :--- |
| **`cdb_core`** | Shared Modelle/Events | `Signal`, `Order`, `OrderResult` | [Design](./deep-issues-lab/cdb_core.md) | [Code](https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/core/domain/models.py) |
| **`cdb_signal`** | Signal-Erzeugung | Publishes: `signals` | [Design](./deep-issues-lab/cdb_signal%20(legacy).md) | [Code](https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/services/signal/service.py) |
| **`cdb_risk`** | Guards/Approval | Sub: `signals`, `order_results` / Pub: `orders` / Stream: `stream.bot_shutdown` | [Design](./deep-issues-lab/cdb_risk.md) | [Code](https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/services/risk/service.py) |
| **`cdb_execution`** | Order Handling / Results | Sub: `orders` / Pub: `order_results` (Topic + Stream `order_results`) | [Design](./deep-issues-lab/cdb_execution.md) | [Code](https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/services/execution/service.py) |
| **`db_writer`** | Persistenz | Sub: `order_results` / Tables: `orders`, `trades` | [Design](./deep-issues-lab/cdb_db_writer.md) | [Code](https://github.com/jannekbuengener/Claire_de_Binare/blob/{{BRANCH}}/services/db_writer/db_writer.py) |
| **PSM** | Portfolio/State Mgmt | (to define) | [Design](./deep-issues-lab/PORTFOLIO%20&%20STATE%20MANAGER%20(PSM).md) | `(not yet)` |

---

## 📊 Systemstatus

| Status | Details |
| :--- | :--- |
| **P0 E2E** | ✅ TC-P0-001/002/005 deterministisch (2× back-to-back) |
| **Offen (bewusst)** | ⏭️ TC-P0-003 (Drawdown Guard), ⏭️ TC-P0-004 (Circuit Breaker aktiv testen) |

---

## ⚡ Runbook (Known-Good Commands)
> **Stack reset + start (BLUE+RED canonical runtime)**
> `docker compose -f infrastructure/compose/compose.blue.yml down -v`
> `docker compose -f infrastructure/compose/compose.red.yml down -v`
> `docker compose -f infrastructure/compose/compose.blue.yml up -d`
> `docker compose -f infrastructure/compose/compose.red.yml up -d`
> `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/compose.red.yml ps`

> **P0 E2E (Determinismus)**
> ```powershell
> $env:E2E_RUN="1"
> $env:E2E_DISABLE_CIRCUIT_BREAKER="1"
> pytest -m e2e tests/e2e/test_paper_trading_p0.py -v -rs --no-cov -p no:cacheprovider
> pytest -m e2e tests/e2e/test_paper_trading_p0.py -v -rs --no-cov -p no:cacheprovider
> ```

> **Redis evidence (Auth)**
> ```bash
> docker compose exec -T cdb_redis redis-cli -a "<REDIS_PASSWORD>" XINFO STREAM order_results
> docker compose exec -T cdb_redis redis-cli -a "<REDIS_PASSWORD>" XLEN order_results
> docker compose exec -T cdb_redis redis-cli -a "<REDIS_PASSWORD>" XRANGE order_results - + COUNT 3
> ```

---

## ⚠️ Change-Safety (nur kontrolliert)

- **`~/Documents/.secrets/.cdb`** (`SECRETS_PATH`) → **niemals committen**, niemals in Docs/Issues.
- **`docker-compose.yml` + Service-Namen/Netzwerk** → nur kleine, reviewte Änderungen (Default-Stack stabil halten).
- **`infrastructure/database/schema.sql`** → Änderungen nur mit Review + E2E 2× back-to-back + klarer Schema-Strategie.
- **`core/domain/*`** → high-impact: systemweiter Check nötig.
- **Stream-/Topic-Namen** → nur ändern, wenn Cockpit/Docs/Tests konsistent nachgezogen werden.
