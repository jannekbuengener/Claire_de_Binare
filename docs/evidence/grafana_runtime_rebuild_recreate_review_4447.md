# Grafana Runtime Rebuild/Recreate Review (#4447)

**Status:** Runtime evidence blocked (docs-only review)

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
| Runtime inspection status | blocked: Docker Desktop Linux Engine pipe `//./pipe/dockerDesktopLinuxEngine` was unavailable |
| Runtime observed container | unavailable — `docker ps --all --filter name=^/cdb_grafana$` could not connect |
| Runtime observed image / image ID | unavailable — `docker inspect` and `docker image inspect` could not connect |
| Runtime mutation performed | `false` |

## Repo-soll

PR #4438 changed the Grafana image in both relevant Compose declarations and
the service catalog from `13.1.2-ubuntu` with digest
`dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45` to the
expected image recorded above. `compose.red.yml` is the direct RED runtime
declaration for the fixed container name `cdb_grafana`.

## Runtime-ist and comparison

The local Docker client reported that the Docker Desktop Linux engine endpoint
does not exist. Consequently, no existing or running `cdb_grafana` container,
its configured image, image ID, or local expected-image presence could be
observed. A Soll/Ist comparison is therefore not possible.

## Verdict

**`BLOCKED_INSUFFICIENT_RUNTIME_EVIDENCE`**

Neither `REBUILD_REQUIRED` nor `NO_REBUILD_REQUIRED` is justified without a
read-only observation of the local `cdb_grafana` container and its image ID.
No runtime action is authorized or implied by this review.

## Missing evidence and exact next read-only step

When the Docker engine is available, obtain only the following evidence before
making the verdict:

```powershell
docker ps --all --filter name=^/cdb_grafana$ --format "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"
docker inspect cdb_grafana --format "{{.Config.Image}}|{{.Image}}"
docker image inspect grafana/grafana:13.1.3-ubuntu@sha256:ab9a06d495291c7ba210426b62e9056dba6046d0945f7e9af041f3ff29b4c7fe --format "{{.Id}}"
```

If the inspected container image ID differs from the expected local image ID,
a later operator session may decide whether to recreate the service. This
review does not perform or authorize that action.

## Validation

- Reviewed PR #4438 merge diff for `base.yml`, `compose.red.yml`, and
  `SERVICE_CATALOG.md`.
- Searched the scoped repository surfaces for `cdb_grafana` and the expected
  Grafana image version.
- Performed only failed read-only Docker inspection attempts; no Docker
  mutation was attempted.

## Guardrails

- LR remains `NO-GO`; no live-capital or trading conclusion follows.
- This is not a Grafana stage gate and does not alter the Board stage.
