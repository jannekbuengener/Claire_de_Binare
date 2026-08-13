# Grafana Runtime Rebuild/Recreate Review (#4447)

**Status:** Review complete (docs-only review)

## Scope and boundaries

This review determines whether the local `cdb_grafana` runtime is aligned with
the image now declared on `origin/main`. It did not pull, build, start, stop,
restart, remove, recreate, or otherwise mutate Docker, containers, images,
volumes, networks, BLUE/RED state, or secrets.

## Evidence

| Field | Observed value |
| --- | --- |
| Source PR | [#4438](https://github.com/jannekbuengener/Claire_de_Binare/pull/4438) — merged |
| Source merge SHA | `dd60fbe62249f1c452067a7ef7509cff10c4541d` |
| Current main SHA | `7ce61bee26ee9b4a7e1f84c49a4b159b3fd7ce3a` |
| Target service | `cdb_grafana` |
| Repo expected image | `grafana/grafana:13.1.3-ubuntu@sha256:ab9a06d495291c7ba210426b62e9056dba6046d0945f7e9af041f3ff29b4c7fe` |
| Relevant Compose path | `infrastructure/compose/compose.red.yml` declares `cdb_grafana` directly; `infrastructure/compose/base.yml` declares the same pin |
| Runtime inspection status | complete: Docker Engine `29.7.2` reachable via read-only inspection |
| Runtime observed container | `911fa71b91b4`, `cdb_grafana`, healthy |
| Runtime observed image / image ID | `grafana/grafana:13.1.2-ubuntu@sha256:dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45` / `sha256:dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45` |
| Runtime mutation performed | `false` |

## Repo-soll

PR #4438 changed the Grafana image in both relevant Compose declarations and
the service catalog from `13.1.2-ubuntu` with digest
`dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45` to the
expected image recorded above. `compose.red.yml` is the direct RED runtime
declaration for the fixed container name `cdb_grafana`.

## Runtime-ist and comparison

The running, healthy `cdb_grafana` container uses the former
`13.1.2-ubuntu` image and its former digest. The expected
`13.1.3-ubuntu` digest is not present locally. The runtime therefore does not
match the current repository declaration.

## Verdict

**`REBUILD_REQUIRED`**

The running container is pinned to the previous image digest, while
`origin/main` declares a new image digest. A rebuild/recreate is required
before the local Grafana runtime can be considered aligned with the current
repository state. No runtime action is authorized or implied by this review.

## Exact later operator step (not executed)

Only after explicit operator approval in the matching RED runtime context:

```powershell
docker compose -f infrastructure/compose/compose.red.yml up -d --force-recreate cdb_grafana
```

Afterward, repeat the same image-safe read-only inspection and require the
expected `13.1.3-ubuntu` digest. This review does not perform or authorize the
operator step.

## Validation

- Reviewed PR #4438 merge diff for `base.yml`, `compose.red.yml`, and
  `SERVICE_CATALOG.md`.
- Searched the scoped repository surfaces for `cdb_grafana` and the expected
  Grafana image version.
- Read-only Docker inspection observed the running old container image and
  confirmed that the expected image is absent locally; no Docker mutation was
  attempted.

## Guardrails

- LR remains `NO-GO`; no live-capital or trading conclusion follows.
- This is not a Grafana stage gate and does not alter the Board stage.
