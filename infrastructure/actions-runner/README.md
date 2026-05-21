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

## Stopping & Removing

**Stop** (runner goes offline, stays registered):

```bash
docker compose -f infrastructure/actions-runner/docker-compose.runner.yml down
```

**Remove** (fully deregister): use the GitHub UI
Settings > Actions > Runners > select runner > Remove, then follow the
displayed removal command. If you rebuild the container without removing the
old entry first, a duplicate runner may appear in the UI.

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
| Volume | `runner-work` | `runner-work-2` |
| Labels | `self-hosted`, `cdb`, `docker` | `self-hosted`, `cdb`, `docker`, `merge-gate` |

### Labels

Runner 2 custom labels: `cdb`, `docker`, `merge-gate`. The default label
`self-hosted` is added automatically by GitHub.
Workflows target: `runs-on: [self-hosted, cdb, docker, merge-gate]`.

**Important**: `runs-on` with multiple labels is hard label matching. GitHub
routes the job only to a runner that has **all** specified labels. There is no
fallback to GitHub-hosted runners.

### Stopping & Removing Runner 2

**Stop**:
```bash
docker compose -f infrastructure/actions-runner/docker-compose.runner2.yml down
```

**Remove** (fully deregister): use the GitHub UI
Settings > Actions > Runners > select `cdb-docker-runner-2` > Remove.
