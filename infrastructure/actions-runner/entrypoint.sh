#!/bin/bash
set -euo pipefail

STATE_DIR="/actions-runner/runner-state"

# ── Required env ────────────────────────────────────────────────
# REPO_URL is always required.
# RUNNER_TOKEN is only required when no persistent state exists
# (neither /actions-runner/.runner nor $STATE_DIR/.runner).
if [ -z "${REPO_URL:-}" ]; then
  echo "ERROR: REPO_URL is not set." >&2
  exit 1
fi

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

# ── Fix volume permissions ────────────────────────────────────────
sudo mkdir -p /actions-runner/_work/_tool /actions-runner/_work/_temp /actions-runner/_work/_update
sudo chown -R runner:runner /actions-runner/_work

# ── Restore runner state from persistent volume ─────────────────
if [ -d "$STATE_DIR" ]; then
  for f in .runner .credentials .credentials_rsaparams .path; do
    if [ -f "$STATE_DIR/$f" ] && [ ! -f "/actions-runner/$f" ]; then
      cp "$STATE_DIR/$f" "/actions-runner/$f"
      echo "Restored $f from persistent state"
    fi
  done
fi

# ── Validate token requirement ──────────────────────────────────
state_exists=false
for f in .runner .credentials .credentials_rsaparams; do
  if [ -f "/actions-runner/$f" ]; then
    state_exists=true
    break
  fi
done

if [ "$state_exists" = "false" ] && [ -z "${RUNNER_TOKEN:-}" ]; then
  echo "ERROR: RUNNER_TOKEN is not set and no persistent runner state found." >&2
  echo "Either provide RUNNER_TOKEN for initial registration or ensure state volume is mounted." >&2
  exit 1
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

# ── Persist runner state to volume ──────────────────────────────
sudo mkdir -p "$STATE_DIR"
for f in .runner .credentials .credentials_rsaparams .path; do
  if [ -f "/actions-runner/$f" ]; then
    cp "/actions-runner/$f" "$STATE_DIR/$f"
  fi
done
sudo chown -R runner:runner "$STATE_DIR"

# ── Graceful shutdown ───────────────────────────────────────────
cleanup() {
  if [ "${RUNNER_DEREGISTER_ON_EXIT:-false}" = "true" ] && [ -n "${RUNNER_TOKEN:-}" ]; then
    echo "Caught signal, deregistering runner (RUNNER_DEREGISTER_ON_EXIT=true)..."
    ./config.sh remove --unattended --token "${RUNNER_TOKEN}" || true
  else
    echo "Caught signal, stopping runner (RUNNER_DEREGISTER_ON_EXIT=${RUNNER_DEREGISTER_ON_EXIT:-false})..."
  fi
  exit 0
}
trap cleanup SIGTERM SIGINT

# ── Start ───────────────────────────────────────────────────────
exec ./run.sh
