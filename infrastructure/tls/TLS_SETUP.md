# TLS/SSL Setup Guide — LEGACY / QUARANTINED

**Issue (original):** #103
**Issue (decision):** #4120
**Status:** LEGACY / QUARANTINED — DO NOT USE
**Decision:** `RETIRE_QUARANTINE`
**Last Updated:** 2026-07-31

---

## Operator notice (read first)

`infrastructure/compose/tls.yml` is **not** part of the canonical BLUE+RED
runtime. Do **not** start the stack with the TLS overlay.

Canonical operator path:

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
# or: .\tools\cdb.ps1 runtime up
```

Secrets canon remains `${SECRETS_PATH}` with default
`~/Documents/.secrets/.cdb`. Historical `.cdb_local/tls` paths in this guide
and in `tls.yml` are **not** the secrets canon and are not a supported
operator workflow.

The PowerShell `-TLS` switch in `infrastructure/scripts/stack_up.ps1` is
fail-closed legacy compatibility: it refuses to attach `tls.yml`.

This document is retained as a **historical reference** only. It must not be
linked from active env/onboarding surfaces as an executable start guide.

---

## Historical overview (archived)

This guide originally documented an experimental TLS/SSL overlay for Redis and
PostgreSQL (Issue #103). That overlay was never reconciled to the BLUE/RED and
`${SECRETS_PATH}` secrets canon and is now quarantined (#4120).

### What the overlay historically attempted

| Component | Intent | Port |
|-----------|--------|------|
| Redis | TLS-only mode | 6379 |
| PostgreSQL | SSL for network connections | 5432 |
| Service-to-Service | Via Redis/PostgreSQL TLS | - |

---

## Historical certificate layout (do not generate here)

Certificate generation and rotation instructions are intentionally **not**
reproduced as an active procedure in this quarantined guide. Do not run
`generate_certs.sh` as part of a normal operator path from this document.

Historical storage path referenced by the overlay (non-canon):

```text
../.cdb_local/tls/   # gitignored; NOT ${SECRETS_PATH}
```

---

## Historical compose overlay shape (do not start)

The quarantined `tls.yml` historically overrode Redis/PostgreSQL commands and
mounted certificates from `.cdb_local/tls`, plus client env such as
`REDIS_TLS=true` and `POSTGRES_SSLMODE=verify-ca`.

Do **not** run:

```text
docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/tls.yml up -d
```

---

## Active SSL-related runtime knobs (without overlay)

Service clients may still honor env knobs such as `POSTGRES_SSLMODE` via
[`core/utils/postgres_client.py`](../../core/utils/postgres_client.py). That is
independent of the quarantined compose overlay. Default operator stacks do not
require `tls.yml`.

---

## Files reference (quarantine map)

```text
infrastructure/
├── tls/
│   ├── generate_certs.sh      # utility; not an operator start path
│   ├── postgres_ssl_init.sh   # historical init helper
│   └── TLS_SETUP.md           # this quarantined documentation
└── compose/
    └── tls.yml                # LEGACY / QUARANTINED overlay

# Historical non-canon host path (do not treat as secrets SSOT):
#   ../.cdb_local/tls/

core/utils/
    ├── redis_client.py        # TLS-aware Redis client factory (env-driven)
    └── postgres_client.py     # SSL-aware PostgreSQL client factory (env-driven)
```

---

## See Also

- [`knowledge/operations/DOCKER_STACK_RUNBOOK.md`](../../knowledge/operations/DOCKER_STACK_RUNBOOK.md) — Stack operations (canonical)
- [`infrastructure/compose/COMPOSE_LAYERS.md`](../compose/COMPOSE_LAYERS.md) — Compose overlay architecture
- [`LEGACY_FILES.md`](../../LEGACY_FILES.md) — Legacy file map
- [`docs/onboarding/core-eventflows/blue_red_runtime_topology.md`](../../docs/onboarding/core-eventflows/blue_red_runtime_topology.md) — BLUE/RED topology
- [`docs/env/index.md`](../../docs/env/index.md) — Env / secrets canon pointers
