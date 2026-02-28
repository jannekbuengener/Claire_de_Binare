#!/bin/bash
set -euo pipefail

# ── Required env ────────────────────────────────────────────────
for var in REPO_URL RUNNER_TOKEN; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: $var is not set." >&2
    exit 1
  fi
done

# ── Docker socket GID alignment (optional) ──────────────────────
# Pass DOCKER_GID matching the host's docker-socket group so the
# non-root runner user can talk to the Docker daemon.
if [ -n "${DOCKER_GID:-}" ]; then
  if sudo groupmod -g "$DOCKER_GID" docker 2>/dev/null; then
    sudo usermod -aG docker runner
    echo "Docker group GID set to $DOCKER_GID"
  else
    sock_group="$(getent group "$DOCKER_GID" | cut -d: -f1)"
    if [ -n "${sock_group:-}" ]; then
      sudo usermod -aG "$sock_group" runner
      echo "Docker socket group already exists as '$sock_group'; added runner to it"
    else
      echo "WARN: could not set docker GID to $DOCKER_GID (may already be taken), continuing..." >&2
    fi
  fi
fi

# ── Configure runner ────────────────────────────────────────────
cd /actions-runner

if [ -f /actions-runner/.runner ]; then
  echo "Runner already configured"
else
  ./config.sh \
    --url "${REPO_URL}" \
    --token "${RUNNER_TOKEN}" \
    --name "${RUNNER_NAME:-cdb-docker-runner-1}" \
    --labels "${RUNNER_LABELS:-cdb,docker}" \
    --work "${RUNNER_WORKDIR:-_work}" \
    --unattended \
    --replace
fi

# ── Graceful shutdown ───────────────────────────────────────────
cleanup() {
  echo "Caught signal, deregistering runner..."
  ./config.sh remove --unattended --token "${RUNNER_TOKEN}" || true
  exit 0
}
trap cleanup SIGTERM SIGINT

# ── Start ───────────────────────────────────────────────────────
exec ./run.sh
