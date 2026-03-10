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
displayed removal command. If you rebuild the container without removing
the old entry first, a duplicate runner may appear in the UI.
