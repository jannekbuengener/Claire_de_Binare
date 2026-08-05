# CDB Agent Environment Profiles v1 (#4255)

Status: Canonical (engineering contract)
Parent: `#4249` / Meta-Epic ACP
Issue: `#4255`
Batch PR: `#4286`

## Purpose

Repo-versionierte, least-privilege **CDB Execution Environment Profiles** plus
fail-closed Environment Doctor / Preflight. Cursor-eigene Config und CDB-Policy
bleiben getrennt.

## Layers

| Layer | Path | Role |
| --- | --- | --- |
| Cursor provider config | `.cursor/environment.json` | Official Cursor schema only |
| CDB profiles | `config/agent-control/profiles/environments/` | Policy ceilings |
| Doctor / Preflight | `tools/agent_control/environment/` | Shared gate for dry-run + execute |
| CLI | `python -m tools.agent_control environment ...` | Validate / offline doctor |

## Build-context invariant (#4360)

`.cursor/environment.json` builds `ci/Dockerfile` with repo-root context (`..`).
Every local `COPY`/`ADD` source in that Dockerfile MUST exist under the context
and MUST NOT be excluded by the context-root `.dockerignore`.

In particular, `requirements-dev.txt` is required by `ci/Dockerfile` (toolchain
SSOT) and must remain visible to the Cursor saved-environment build. Contract
enforcement: `tools/agent_control/environment/dockerfile_context.py` and
`tests/unit/infra/test_cursor_environment_dockerfile_context.py`.

## Governed profile IDs

- `cdb-docs-readonly.v1`
- `cdb-agent-skills.v1`
- `cdb-python-fast.v1`
- `cdb-ci-debug.v1`
- `cdb-validation-research.v1`
- `cdb-runtime-risk-restricted.v1`

Legacy fixtures keep `mock.v1` / `local_repo.v1` (minimal fields).

## Verdicts

- `READY_OFFLINE_ONLY` — schema-valid offline; `execute_ready=false`
- `READY_FOR_RECORDED_TEST` — fixture attestation only; never live
- `BLOCKED` / `UNKNOWN` / `UNAVAILABLE` — non-zero CLI; blocks execute

## Hard rules

- `live_dispatch_allowed=false` and `max_live_cost_usd=0` for all #4255 profiles
- Setup failed / unknown / not_run is never READY for execute
- Fallback true/unknown is BLOCKED
- Opaque snapshot ID is not a trusted base identity
- Environment SUCCESS is not PASS, not merge authority, not `cdb-local-ci`
- Live Cursor dispatch remains forbidden pending `#4256`–`#4258`

## CLI

```bash
python -m tools.agent_control environment validate --config config/agent-control
python -m tools.agent_control environment validate --profile cdb-agent-skills.v1 \
  --config config/agent-control
python -m tools.agent_control environment doctor --profile cdb-agent-skills.v1 \
  --config config/agent-control --offline
python -m tools.agent_control environment doctor --profile cdb-agent-skills.v1 \
  --config config/agent-control \
  --attestation docs/contracts/examples/agent_environment/positive_recorded_attestation.json
```
