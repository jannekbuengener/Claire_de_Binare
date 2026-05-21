#!/bin/bash
set -euo pipefail

STATE_DIR="/actions-runner/runner-state"

# ── Guard all RUNNER_TOKEN access ────────────────────────────────
# Single declared variable; never reference ${RUNNER_TOKEN} directly
# under set -u — always use $runner_token instead.
runner_token="${RUNNER_TOKEN:-}"

# ── Required env ────────────────────────────────────────────────
# REPO_URL is always required.
# RUNNER_TOKEN is only required when no complete runner state exists
# (complete = .runner + .credentials + .credentials_rsaparams all present).
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
  for f in .runner .credentials .credentials_rsaparams; do
    if [ -f "$STATE_DIR/$f" ] && [ ! -f "/actions-runner/$f" ]; then
      cp "$STATE_DIR/$f" "/actions-runner/$f"
      echo "Restored $f from persistent state"
    fi
  done
  # .path is optional
  if [ -f "$STATE_DIR/.path" ] && [ ! -f "/actions-runner/.path" ]; then
    cp "$STATE_DIR/.path" "/actions-runner/.path"
    echo "Restored .path from persistent state"
  fi
fi

# ── Classify runner state ────────────────────────────────────────
# Required files for a complete state: .runner, .credentials,
# .credentials_rsaparams.  .path is optional.
# complete_active  → all three required files present → skip registration
# partial_state    → some but not all present → need token to re-register
# (no state)       → need token for initial registration
_has_runner=false
_has_credentials=false
_has_rsaparams=false

[ -f "/actions-runner/.runner" ]                && _has_runner=true
[ -f "/actions-runner/.credentials" ]          && _has_credentials=true
[ -f "/actions-runner/.credentials_rsaparams" ] && _has_rsaparams=true

_complete_state=false
_partial_state=false

if [ "$_has_runner" = "true" ] && [ "$_has_credentials" = "true" ] && [ "$_has_rsaparams" = "true" ]; then
  _complete_state=true
elif [ "$_has_runner" = "true" ] || [ "$_has_credentials" = "true" ] || [ "$_has_rsaparams" = "true" ]; then
  _partial_state=true
fi

# ── Decide registration path ─────────────────────────────────────
if [ "$_complete_state" = "true" ]; then
  echo "Complete runner state found — skipping registration"
elif [ "$_partial_state" = "true" ]; then
  if [ -z "$runner_token" ]; then
    echo "ERROR: Partial runner state detected but RUNNER_TOKEN is not set." >&2
    echo "Provide RUNNER_TOKEN for re-registration, or remove partial state and provide a fresh token." >&2
    exit 1
  fi
  echo "Partial runner state detected — re-registering with token"
elif [ -z "$runner_token" ]; then
  echo "ERROR: RUNNER_TOKEN is not set and no runner state found." >&2
  echo "Either provide RUNNER_TOKEN for initial registration or ensure state volume is mounted." >&2
  exit 1
fi

# ── Configure runner ────────────────────────────────────────────
cd /actions-runner

if [ "$_complete_state" = "true" ]; then
  echo "Runner already configured"
else
  ./config.sh \
    --url "${REPO_URL}" \
    --token "$runner_token" \
    --name "${RUNNER_NAME:-cdb-docker-runner-1}" \
    --labels "${RUNNER_LABELS:-cdb,docker}" \
    --work "${RUNNER_WORKDIR:-_work}" \
    --unattended \
    --replace
fi

# ── Persist runner state to volume ──────────────────────────────
# On a fresh Docker volume the mount point is root:root, so we must
# fix ownership *before* the unprivileged cp — otherwise set -e
# kills the container before chown is ever reached.
sudo mkdir -p "$STATE_DIR"
sudo chown -R runner:runner "$STATE_DIR"
for f in .runner .credentials .credentials_rsaparams .path; do
  if [ -f "/actions-runner/$f" ]; then
    cp "/actions-runner/$f" "$STATE_DIR/$f"
  fi
done
sudo chown -R runner:runner "$STATE_DIR"

# ── Graceful shutdown ───────────────────────────────────────────
cleanup() {
  if [ "${RUNNER_DEREGISTER_ON_EXIT:-false}" = "true" ] && [ -n "$runner_token" ]; then
    echo "Caught signal, deregistering runner (RUNNER_DEREGISTER_ON_EXIT=true)..."
    ./config.sh remove --unattended --token "$runner_token" || true
  else
    echo "Caught signal, stopping runner (RUNNER_DEREGISTER_ON_EXIT=${RUNNER_DEREGISTER_ON_EXIT:-false})..."
  fi
  exit 0
}
trap cleanup SIGTERM SIGINT

# ── Start ───────────────────────────────────────────────────────
exec ./run.sh
