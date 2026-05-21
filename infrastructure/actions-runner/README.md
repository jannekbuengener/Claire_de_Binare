# Self-Hosted GitHub Actions Runner

Containerized GitHub Actions runner for CDB required checks.

## Quick Start

1. **Generate token**: Settings > Actions > Runners > New self-hosted runner > copy token
2. **Configure**:
   ```bash
   cp .env.runner.example .env.runner
   # paste RUNNER_TOKEN into .env.runner
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

## Runner 2 — Dedicated Merge-Gate Runner

Runner 2 is a second self-hosted runner dedicated to merge-blocking required
checks (`ci`, `policy-gate`). It uses its own env file, container name, runner
name, volume, and labels — completely independent from Runner 1.

### Quick Start

1. **Generate token**: Settings > Actions > Runners > New self-hosted runner > copy token
2. **Configure**:
   ```bash
   cp .env.runner2.example .env.runner2
   # paste RUNNER_TOKEN into .env.runner2
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
Workflows target: `runs-on: [self-hosted, cdb, docker, merge-gate]`.

**Important**: `runs-on` with multiple labels is hard label matching. GitHub
routes the job only to a runner that has **all** specified labels. There is no
fallback to GitHub-hosted runners.

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
