# Claire de Binare Docker Stack Inventory

**Status:** Canonical runtime pointer for the working repo.

## Canonical runtime

- **Operator/runtime canon:** `infrastructure/compose/compose.blue.yml` + `infrastructure/compose/compose.red.yml`
- **Canonical start helper:** `infrastructure/scripts/setup_blue_red.ps1`
- **Canonical runtime references:** `knowledge/systems/STACK_LIFECYCLE.md`, `knowledge/OPERATIONS_RUNBOOK.md`, `knowledge/content/ONBOARDING_LINKS.md`, `infrastructure/compose/COMPOSE_LAYERS.md`

## Compose layers + intent

| File | Intent | Status |
| --- | --- | --- |
| `infrastructure/compose/compose.blue.yml` | BLUE runtime services | Canonical |
| `infrastructure/compose/compose.red.yml` | RED runtime services | Canonical |
| `infrastructure/compose/logging.yml` | Logging overlay: Loki + Promtail + Alertmanager | Optional overlay — nicht Teil des Standard-BLUE/RED-Starts |
| `infrastructure/compose/base.yml` | Shared/legacy compose fragment | Legacy: CI/test and explicit compatibility flows only |
| `infrastructure/compose/dev.yml` | Legacy dev overlay | Legacy: CI/test and explicit compatibility flows only |
| `infrastructure/scripts/setup_blue_red.ps1` | Start BLUE/RED runtime | Canonical |
| `infrastructure/scripts/` compatibility helpers | Legacy helper scripts for `base.yml` flows | Legacy |

## Canonical runtime invocation

```powershell
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

Stop:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml down
docker compose -f infrastructure/compose/compose.red.yml down
```

## Inventory notes

- This document intentionally uses repo-relative paths only. Host-specific URI links are not canonical.
- Local secret directories, `.env` files, and host log paths are environment-specific and must be resolved at runtime, not hard-coded as inventory canon.
- The retired root-level legacy compose entry point is not part of the current working repo and must not be treated as an active runtime entry point.
- `tools/paper_trading/Dockerfile` exists in the current repo and is not a missing artifact.

## Legacy snapshot boundary

- Earlier versions of this document mixed host-bound links with the legacy root/base/dev compose chain and presented them as active canon.
- The old per-service matrix is intentionally retired here until it is regenerated from the current BLUE/RED compose sources.
- Until such a regeneration exists, use the canonical runtime files above plus `knowledge/systems/STACK_LIFECYCLE.md` and `knowledge/OPERATIONS_RUNBOOK.md` for operational truth.
