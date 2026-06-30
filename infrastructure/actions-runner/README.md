# Self-Hosted GitHub Actions Runner

Containerized GitHub Actions runner for CDB required checks.

## Quick Start

1. **Generate token**: Settings > Actions > Runners > New self-hosted runner > copy token
2. **Configure**:
   ```bash
   cp .env.runner.example .env.runner
   # paste a bootstrap-only RUNNER_TOKEN into .env.runner
   ```
3. **Start**:
   ```bash
   docker compose -f infrastructure/actions-runner/docker-compose.runner.yml up -d --build
   ```
4. **Verify**:
   ```bash
   docker compose -f infrastructure/actions-runner/docker-compose.runner.yml logs -f
   # Expected: "Listening for Jobs"
   ```

## Docker Socket Access

If workflows need Docker commands, the host socket is mounted.
For non-root access set `DOCKER_GID` in `.env.runner` to match the host:

```bash
stat -c '%g' /var/run/docker.sock   # find GID on host
```

## Labels

Custom labels: `cdb, docker`. The default label `self-hosted` is added
automatically by GitHub.
Workflows target: `runs-on: [self-hosted, cdb]`.

## Token Refresh

The registration token (from GitHub UI) expires after 1 hour, but it is
only needed for the initial `config.sh` call. Once registered the runner
authenticates with its own credentials stored in `.runner`/`.credentials`.
A new token is required only when the container is rebuilt from scratch
or after a manual "Remove runner" in the GitHub UI.

Treat `RUNNER_TOKEN` as a **bootstrap-only / registration-only** credential.
Do not keep it in plaintext local env files longer than needed for initial
registration or a deliberate re-registration window.

## State Persistence

Runner credentials (`.runner`, `.credentials`, `.credentials_rsaparams`,
`.path`) are persisted in a dedicated Docker volume (`runner-state` for
Runner 1, `runner-state-2` for Runner 2). This allows container
rebuilds without re-registration.

**How it works**:
- On startup, the entrypoint restores credentials from the state volume
  before checking whether registration is needed.
- After registration, credentials are copied to the state volume.
- If the state volume contains valid credentials, `RUNNER_TOKEN` is not
  required. The runner reconnects automatically.

**First-time setup** still requires `RUNNER_TOKEN`. After that, rebuilds
(`docker compose down && docker compose up -d --build`) do not need a
new token.

After successful registration, remove or blank the token in `.env.runner`
unless you are intentionally keeping a short-lived local file for a planned
re-registration or deregistration step.

### Complete vs Partial State

The entrypoint distinguishes three registration paths:

| State | Condition | Behavior |
|-------|-----------|----------|
| **Complete** | `.runner` + `.credentials` + `.credentials_rsaparams` all present | Skip registration, reconnect |
| **Partial** | Some but not all required files present | Require `RUNNER_TOKEN` for re-registration, or exit with clear error |
| **None** | No state files present | Require `RUNNER_TOKEN` for initial registration, or exit with clear error |

A **partial state** can occur if the state volume is corrupted or only
partially restored. In this case the runner cannot self-heal without a
fresh `RUNNER_TOKEN`. The entrypoint will print a descriptive error and
exit rather than crash with an unbound-variable error.

## Deregistration

By default, stopping the container (`docker compose down`) does **not**
deregister the runner from GitHub. The runner stays registered and
reconnects on the next start.

To intentionally deregister (e.g. before decommissioning a runner), set
`RUNNER_DEREGISTER_ON_EXIT=true` in `.env.runner` / `.env.runner2`. This
requires `RUNNER_TOKEN` to be present.

```bash
# Normal stop — runner stays registered
docker compose -f infrastructure/actions-runner/docker-compose.runner.yml down

# Intentional removal — set RUNNER_DEREGISTER_ON_EXIT=true first
# Then stop the container. The runner will deregister from GitHub.
```

## Stopping & Removing

**Stop** (runner goes offline, stays registered):

```bash
docker compose -f infrastructure/actions-runner/docker-compose.runner.yml down
```

**Remove** (fully deregister): set `RUNNER_DEREGISTER_ON_EXIT=true` in
`.env.runner`, then stop the container; or use the GitHub UI
Settings > Actions > Runners > select runner > Remove.

## Security Notice

**This repository is PUBLIC.** Anyone can fork and submit pull requests.

As of PR #3405, the merge-blocking required checks (`ci`, `policy-gate`) run on
**GitHub-hosted `ubuntu-latest` runners**, not on self-hosted runners. This
prevents untrusted fork-PR code from executing on the privileged self-hosted
runner with Docker socket access.

**Rules:**
- No `pull_request`-triggered workflow may target the self-hosted runner.
- Self-hosted runners (`cdb-docker-runner-1`, `cdb-docker-runner-2`) are
  reserved exclusively for `workflow_dispatch` and `schedule` triggers.
- Before adding a new `pull_request` workflow on a self-hosted runner, verify
  that it cannot be reached by untrusted fork PRs.
- Docker socket (`/var/run/docker.sock`) remains mounted in the compose files
  for workflows that need Docker commands. `NOPASSWD:ALL` (unrestricted root) is
  replaced with a restricted sudo rule limited to `chown`, `mkdir`, `groupmod`,
  and `usermod` — exactly what the entrypoint needs. If Docker-in-Docker is not
  needed for a job, remove the socket mount.

**Secret hygiene:**
- Never print real `RUNNER_TOKEN` values into logs, issues, commits, PRs, or screenshots.
- `.env.runner` and `.env.runner2` are local-only ops files, not repo artifacts.
- Runner secret files are excluded from the local Docker build context via
  `infrastructure/actions-runner/.dockerignore`.

**Compose-project hygiene:**
- Both runner compose files now declare an explicit `name:` (`cdb_gh_runner` / `cdb_gh_runner_2`)
  so the runner stack always gets its own Compose project regardless of working directory
  or any inherited `COMPOSE_PROJECT_NAME`.
- A global or inherited `COMPOSE_PROJECT_NAME` can still override this — do not set
  `COMPOSE_PROJECT_NAME` globally when running runner compose files.
- Docker-project isolation cleanup (live migration of existing containers) remains tracked
  separately in `#3571`.

## Runner 2 — Dedicated Merge-Gate Runner

Runner 2 is a second self-hosted runner. It was originally dedicated to
merge-blocking required checks (`ci`, `policy-gate`) — those checks now run on
GitHub-hosted runners. Runner 2 remains available for `workflow_dispatch` jobs
that need self-hosted capabilities. It uses its own env file, container name,
runner name, volume, and labels — completely independent from Runner 1.

### Quick Start

1. **Generate token**: Settings > Actions > Runners > New self-hosted runner > copy token
2. **Configure**:
   ```bash
   cp .env.runner2.example .env.runner2
   # paste a bootstrap-only RUNNER_TOKEN into .env.runner2
   ```
3. **Start**:
   ```bash
   docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml up -d --build
   ```
4. **Verify**:
   ```bash
   docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml logs -f
   # Expected: "Listening for Jobs"
   ```

### Key Differences from Runner 1

| Property | Runner 1 | Runner 2 |
|---|---|---|
| Container name | `cdb_gh_runner` | `cdb_gh_runner_2` |
| Env file | `.env.runner` | `.env.runner2` |
| Runner name | `cdb-docker-runner-1` | `cdb-docker-runner-2` |
| Work volume | `runner-work` | `runner-work-2` |
| State volume | `runner-state` | `runner-state-2` |
| Labels | `self-hosted`, `cdb`, `docker` | `self-hosted`, `cdb`, `docker`, `merge-gate` |

### Labels

Runner 2 custom labels: `cdb`, `docker`, `merge-gate`. The default label
`self-hosted` is added automatically by GitHub.
Workflows target: `runs-on: [self-hosted, cdb, docker, merge-gate]` for
`workflow_dispatch` jobs only.

**Important**: `runs-on` with multiple labels is hard label matching. GitHub
routes the job only to a runner that has **all** specified labels. There is no
fallback to GitHub-hosted runners. This is why the required checks were moved
to `ubuntu-latest` — they no longer depend on the self-hosted runner being
available.

### Stopping & Removing Runner 2

**Stop** (runner stays registered):
```bash
docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml down
```

**Remove** (fully deregister): set `RUNNER_DEREGISTER_ON_EXIT=true` in
`.env.runner2`, then stop the container; or use the GitHub UI
Settings > Actions > Runners > select `cdb-docker-runner-2` > Remove.

## Rebuild Without Token

After the initial registration, the runner credentials are persisted in the
state volume. Rebuilding the container does not require a new token:

```bash
# Rebuild without re-registration
docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml down
docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml up -d --build
# Logs should show: "Restored .runner from persistent state"
# or: "Runner already configured"
```

If the state volume is deleted or corrupted, a new `RUNNER_TOKEN` is required
for re-registration.

As with Runner 1, remove or blank the token in `.env.runner2` after successful
registration unless you are in an intentional re-registration or deregistration window.

## Rollback

If state persistence causes issues:

1. Remove state volume mounts from compose files.
2. Revert `entrypoint.sh` to the previous version.
3. Volumes remain on disk — do not delete them unless intentionally
   clearing state.
4. If state is corrupted: generate a new `RUNNER_TOKEN`, remove the old
   runner entry from the GitHub UI, and re-register.

## Maintenance Window

When restarting or rebuilding a runner that handles required merge checks
(`ci`, `policy-gate`), avoid doing so while a check is running. Check
the GitHub Actions queue or runner busy status before stopping.
