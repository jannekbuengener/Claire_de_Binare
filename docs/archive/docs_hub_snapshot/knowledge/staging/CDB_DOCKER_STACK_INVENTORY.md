# Claire de Binare Docker Stack Inventory

## Canonical paths
- [Repo Root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare)
- [Docs Root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare_Docs)
- [Compose env file](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/.cdb_local/.secrets/.env.compose)
- [Secrets directory](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets)

## Compose layers + intent
| File | Purpose | Link |
| --- | --- | --- |
| `docker-compose.base.yml` | Entry point that wires every service, secret, config, and named volume for production-like runs. | [Compose: docker-compose.base.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) |
| `infrastructure/compose/base.yml` | Infrastructure services (Redis, Postgres, Prometheus, Grafana) plus shared configs/secrets inherited by the base stack. | [Compose: infrastructure/compose/base.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/compose/base.yml) |
| `infrastructure/compose/dev.yml` | Development overrides that publish ports, mount host logs, and relax access without touching Dockerfiles or build contexts. | [Compose: infrastructure/compose/dev.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/compose/dev.yml) |

## Compose invocation
Always run compose with these args (scripts below wrap this command):
```
docker compose --env-file .\.cdb_local\.secrets\.env.compose -f docker-compose.base.yml -f infrastructure\compose\base.yml -f infrastructure\compose\dev.yml
```

## Services
| Service | Type | Build context | Build context Link | Dockerfile | Dockerfile Link | Compose Source | Compose Source Link | Image | Container name | Depends on | Ports | Healthcheck |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cdb_redis` | image | n/a | n/a | n/a | n/a | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `redis:7-alpine` | `cdb_redis` | none | `6379` | `redis-cli -a /run/secrets/redis_password ping` |
| `cdb_postgres` | image | n/a | n/a | n/a | n/a | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `postgres:15-alpine` | `cdb_postgres` | none | `5432` | `pg_isready -U claire_user -d claire_de_binare` |
| `cdb_prometheus` | image | n/a | n/a | n/a | n/a | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `prom/prometheus:latest` | `cdb_prometheus` | none | `19090->9090` | `wget -qO- http://localhost:9090/-/healthy` |
| `cdb_grafana` | image | n/a | n/a | n/a | n/a | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `grafana/grafana:latest` | `cdb_grafana` | `cdb_prometheus` | `3000` | `curl -fsS http://localhost:3000/api/health` |
| `cdb_core` | build | `.` (repo root) | [Repo root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare) | `services/signal/Dockerfile` | [Dockerfile: services/signal/Dockerfile](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/services/signal/Dockerfile) | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `claire_de_binare-cdb_core` | `cdb_core` | `cdb_redis, cdb_postgres` | `8001->8000` | `curl -fsS http://localhost:8001/health` |
| `cdb_risk` | build | `.` | [Repo root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare) | `services/risk/Dockerfile` | [Dockerfile: services/risk/Dockerfile](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/services/risk/Dockerfile) | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `claire_de_binare-cdb_risk` | `cdb_risk` | `cdb_core, cdb_redis, cdb_postgres` | `8002->8000` | `curl -fsS http://localhost:8002/health` |
| `cdb_execution` | build | `.` | [Repo root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare) | `services/execution/Dockerfile` | [Dockerfile: services/execution/Dockerfile](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/services/execution/Dockerfile) | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `claire_de_binare-cdb_execution` | `cdb_execution` | `cdb_risk, cdb_redis, cdb_postgres` | `8003->8000` | `curl -fsS http://localhost:8003/health` |
| `cdb_db_writer` | build | `.` | [Repo root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare) | `services/db_writer/Dockerfile` | [Dockerfile: services/db_writer/Dockerfile](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/services/db_writer/Dockerfile) | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `claire_de_binare-cdb_db_writer` | `cdb_db_writer` | `cdb_redis, cdb_postgres` | `internal only` | `CMD true` |
| `cdb_paper_runner` | build | `.` | [Repo root](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare) | `tools/paper_trading/Dockerfile` | [Dockerfile: tools/paper_trading/Dockerfile](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/tools/paper_trading/Dockerfile) | `docker-compose.base.yml` | [Base compose](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml) | `claire_de_binare-cdb_paper_runner` | `cdb_paper_runner` | `cdb_core, cdb_execution, cdb_postgres, cdb_redis, cdb_risk` | `internal 8004` | `curl -fsS http://localhost:8004/health` |

## Service dependency links
- **cdb_core**
  - Depends on: `cdb_redis`, `cdb_postgres`
  - Volumes: host bind [C:/Users/janne/Documents/GitHub/logs](file:///C:/Users/janne/Documents/GitHub/logs) → `/app/logs`
  - Secrets: [redis_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/redis_password), [postgres_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/postgres_password), [grafana_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/grafana_password), [GITHUB_TOKEN](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/GITHUB_TOKEN) *(Status: MISSING (file not present yet))*.
  - Healthcheck: `curl -fsS http://localhost:8001/health`
- **cdb_risk**
  - Depends on: `cdb_core`, `cdb_redis`, `cdb_postgres`
  - Volumes: named `risk_logs` → `/logs`; host bind [C:/Users/janne/Documents/GitHub/logs](file:///C:/Users/janne/Documents/GitHub/logs) → `/app/logs`
  - Secrets: `redis_password`, `postgres_password`, `grafana_password`, `GITHUB_TOKEN` *(Status: MISSING)*
  - Healthcheck: `curl -fsS http://localhost:8002/health`
- **cdb_execution**
  - Depends on: `cdb_risk`, `cdb_redis`, `cdb_postgres`
  - Volumes: host bind [C:/Users/janne/Documents/GitHub/logs](file:///C:/Users/janne/Documents/GitHub/logs) → `/app/logs`
  - Secrets: `redis_password`, `postgres_password`, `grafana_password`, `GITHUB_TOKEN` *(Status: MISSING)*
  - Healthcheck: `curl -fsS http://localhost:8003/health`
- **cdb_db_writer**
  - Depends on: `cdb_redis`, `cdb_postgres`
  - Secrets: `redis_password`, `postgres_password`, `grafana_password`, `GITHUB_TOKEN` *(Status: MISSING)*
  - Healthcheck: `CMD true`
- **cdb_paper_runner**
  - Depends on: `cdb_core`, `cdb_execution`, `cdb_postgres`, `cdb_redis`, `cdb_risk`
  - Volumes: named `logs_data` → `/app/logs`; named `paper_runner_data` → `/app/data`
  - Secrets: `redis_password`, `postgres_password`, `grafana_password`, `GITHUB_TOKEN` *(Status: MISSING)*
  - Healthcheck: `curl -fsS http://localhost:8004/health`
- **Infrastructure services (cdb_grafana, cdb_prometheus, cdb_postgres, cdb_redis)**
  - Grafana binds: [infrastructure/monitoring/grafana/provisioning/datasources](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/monitoring/grafana/provisioning/datasources) and [infrastructure/monitoring/grafana/provisioning/dashboards](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/monitoring/grafana/provisioning/dashboards) → provisioned mounts.
  - Grafana dashboards: [infrastructure/monitoring/grafana/dashboards](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/monitoring/grafana/dashboards) → `/var/lib/grafana/dashboards`
  - Prometheus config: [infrastructure/monitoring/prometheus.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/monitoring/prometheus.yml) mounted to `/etc/prometheus/prometheus.yml`
  - Secrets: `grafana_password`, `postgres_password`, `redis_password` as applicable (via Docker secrets at `/run/secrets/<name>`)

## Secrets & env contract
- **Env keys referenced (names only):** `ACCOUNT_EQUITY`, `DRY_RUN`, `E2E_DISABLE_CIRCUIT_BREAKER`, `GF_SECURITY_ADMIN_PASSWORD__FILE`, `GF_SECURITY_ADMIN_USER`, `GF_USERS_ALLOW_SIGN_UP`, `GITHUB_TOKEN_FILE`, `MEXC_API_KEY_FILE`, `MEXC_API_SECRET_FILE`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PASSWORD`, `POSTGRES_PASSWORD_FILE`, `POSTGRES_PORT`, `POSTGRES_USER`, `REDIS_DB`, `REDIS_HOST`, `REDIS_PASSWORD`, `REDIS_PASSWORD_FILE`, `SIGNAL_STRATEGY_ID`, `STACK_NAME`, `TRADING_MODE`, `NETWORK`, `LOG_LEVEL`, `MAX_DAILY_DRAWDOWN_PCT`, `MAX_POSITION_PCT`, `MAX_SLIPPAGE_PCT`, `MAX_TOTAL_EXPOSURE_PCT`.
- **Runtime Docker secrets (canonical file + status):**

| Secret | Path | Status |
| --- | --- | --- |
| `GITHUB_TOKEN` | [Secret: GITHUB_TOKEN](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/GITHUB_TOKEN) | MISSING (file not present yet) |
| `MEXC_API_KEY` | [Secret: MEXC_API_KEY](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/MEXC_API_KEY) | PRESENT |
| `MEXC_API_SECRET` | [Secret: MEXC_API_SECRET](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/MEXC_API_SECRET) | PRESENT |
| `postgres_password` | [Secret: postgres_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/postgres_password) | PRESENT |
| `redis_password` | [Secret: redis_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/redis_password) | PRESENT |
| `grafana_password` | [Secret: grafana_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/grafana_password) | PRESENT |

- **`*_FILE` references and canonical files:**
  - `GF_SECURITY_ADMIN_PASSWORD__FILE`: `/run/secrets/grafana_password` (populated from [Secret: grafana_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/grafana_password))
  - `GRAFANA_PASSWORD_FILE`: [Secret: grafana_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/grafana_password)
  - `GITHUB_TOKEN_FILE`: [Secret: GITHUB_TOKEN](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/GITHUB_TOKEN) *(Status: MISSING (file not present yet))*
  - `MEXC_API_KEY_FILE`: [Secret: MEXC_API_KEY](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/MEXC_API_KEY) *(Status: PRESENT)*
  - `MEXC_API_SECRET_FILE`: [Secret: MEXC_API_SECRET](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/MEXC_API_SECRET) *(Status: PRESENT)*
  - `POSTGRES_PASSWORD_FILE`: [Secret: postgres_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/postgres_password)
  - `REDIS_PASSWORD_FILE`: [Secret: redis_password](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets/redis_password)
- **External/non-runtime secrets (not part of the Docker stack):** `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` (agent/CLI credentials, intentionally excluded from this inventory).
- **No plaintext secrets** are stored directly in compose; values flow via `_FILE` references or Docker secrets sourced from the directory above.

## Networks
- The stack defines the logical `cdb_network` bridge; compose sets the explicit Docker name to `claire_de_binare_cdb_network`. All active services attach to this bridge.
- **Inspection tip:** `docker network inspect claire_de_binare_cdb_network` lists the infra/app containers described above.

## Volumes
- **Named volumes (preserved across restarts):**
  - `redis_data` → `/data` (`cdb_redis`)
  - `postgres_data` → `/var/lib/postgresql/data` (`cdb_postgres`)
  - `prom_data` → `/prometheus` (`cdb_prometheus`)
  - `grafana_data` → `/var/lib/grafana` (`cdb_grafana`)
  - `risk_logs` → `/logs` (`cdb_risk`)
  - `paper_runner_data` → `/app/data` (`cdb_paper_runner`)
  - `logs_data` → `/app/logs` (`cdb_paper_runner`)
- **Host binds from the dev override:**
  - [C:/Users/janne/Documents/GitHub/logs](file:///C:/Users/janne/Documents/GitHub/logs) → `/app/logs` (attached to `cdb_core`, `cdb_execution`, `cdb_risk`)
  - Grafana/Prometheus provisioning directories already listed above attach via the references in the “Service dependency links” section.
- **Persistence rule:** do not run `docker compose down -v`; named volumes stay intact and the start/stop helpers below honor that rule.

## Runbook
- **Start:** [script: stack_up.ps1](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/scripts/stack_up.ps1) (runs `docker compose --env-file .\.cdb_local\.secrets\.env.compose -f docker-compose.base.yml -f infrastructure\compose\base.yml -f infrastructure\compose\dev.yml up -d` for the infra/app services and waits up to 120 seconds for them to become healthy).
- **Stop:** [script: stack_down.ps1](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/scripts/stack_down.ps1) (runs the same compose args with `down` and no `-v`, preserving named volumes).
- **Restart:** run the stop script above followed by the start script.
- **Troubleshooting commands:**
  - `docker compose --env-file .\.cdb_local\.secrets\.env.compose -f docker-compose.base.yml -f infrastructure\compose\base.yml -f infrastructure\compose\dev.yml ps --format json`
  - `docker compose --env-file .\.cdb_local\.secrets\.env.compose -f docker-compose.base.yml -f infrastructure\compose\base.yml -f infrastructure\compose\dev.yml logs --no-color --tail 200 <service>`
  - `docker network inspect claire_de_binare_cdb_network`

## Freeze notes
- The stack is in AUDIT + FREEZE mode: do not edit compose files, Dockerfiles, secret layouts, or networks; only run verification, documentation, or scripting work documented here.
- All build contexts remain inside `Claire_de_Binare`, and the start/stop helpers above are the official entry points for this phase.

## Automation contract
- This inventory encapsulates the canonical compose invocation, service wiring, runtime secrets, and helper scripts required to bootstrap the stack; no other source is needed to regenerate `stack_up.ps1`/`stack_down.ps1`.
- Automation should read the “Compose invocation” command plus the helper script paths above to derive the exact CLI needed and validate prerequisite files (compose layers, Dockerfiles, scripts, and secrets) before running.
- The “Services” table, dependency links, network, and volume sections provide the relationship graph that a deploy script can use to confirm service ordering, healthcheck targets, and named resources before promoting the stack to green.

## Quick Links Index
- [Compose: docker-compose.base.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/docker-compose.base.yml)
- [Compose: infrastructure/compose/base.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/compose/base.yml)
- [Compose: infrastructure/compose/dev.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/compose/dev.yml)
- [Script: stack_up.ps1](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/scripts/stack_up.ps1)
- [Script: stack_down.ps1](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/scripts/stack_down.ps1)
- [Monitoring: infrastructure/monitoring/prometheus.yml](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare/infrastructure/monitoring/prometheus.yml)
- [Secrets directory](file:///C:/Users/janne/Documents/GitHub/Workspaces/.cdb_local/.secrets)
- [Inventory document](file:///C:/Users/janne/Documents/GitHub/Workspaces/Claire_de_Binare_Docs/knowledge/stack/CDB_DOCKER_STACK_INVENTORY.md)
