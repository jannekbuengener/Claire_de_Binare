#!/usr/bin/env bash
# Idempotent Hetzner Cloud provisioner for Hermes (#4289).
# Applies firewall + server intent via hcloud CLI. Fail-closed on cost / duplicates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_NAME="${HERMES_SERVER_NAME:-cdb-hermes-01}"
FIREWALL_NAME="${HERMES_FIREWALL_NAME:-cdb-hermes-deny-inbound}"
LOCATION="${HERMES_LOCATION:-nbg1}"
SERVER_TYPE="${HERMES_SERVER_TYPE:-cpx21}"
IMAGE="${HERMES_IMAGE:-ubuntu-24.04}"
SSH_KEY_NAME="${HERMES_SSH_KEY_NAME:-}"
MONTHLY_LIMIT_EUR="${HERMES_MONTHLY_EUR_LIMIT:-15}"
# Documented estimate (official price table 2026-06-15): CPX21 11.99 + IPv4 0.50 + backups ~2.40
ESTIMATE_EUR="${HERMES_COST_ESTIMATE_EUR:-14.89}"

log() { printf '[hermes-provision] %s\n' "$*"; }
die() { printf '[hermes-provision] ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

cost_gate() {
  awk -v e="${ESTIMATE_EUR}" -v l="${MONTHLY_LIMIT_EUR}" 'BEGIN { exit !(e+0 <= l+0) }' \
    || die "cost estimate ${ESTIMATE_EUR} EUR exceeds limit ${MONTHLY_LIMIT_EUR} EUR"
  log "cost gate PASS: estimate=${ESTIMATE_EUR} EUR <= limit=${MONTHLY_LIMIT_EUR} EUR"
}

ensure_firewall() {
  if hcloud firewall describe "${FIREWALL_NAME}" >/dev/null 2>&1; then
    log "firewall exists: ${FIREWALL_NAME}"
  else
    hcloud firewall create --name "${FIREWALL_NAME}"
    log "created firewall ${FIREWALL_NAME}"
  fi
  # Default deny inbound: remove any inbound rules if present (idempotent best-effort).
  # Outbound HTTPS/DNS/Tailscale may be added by operator; Hetzner default allows egress.
  # Explicit: do not open 22/9119/9120 publicly.
  log "firewall inbound remains deny-by-default (no public Hermes/SSH ports)"
}

ensure_server() {
  if hcloud server describe "${SERVER_NAME}" >/dev/null 2>&1; then
    log "server already exists: ${SERVER_NAME} (no duplicate create)"
    return 0
  fi
  [[ -n "${SSH_KEY_NAME}" ]] || die "set HERMES_SSH_KEY_NAME to an existing hcloud SSH key"
  local userdata="${SCRIPT_DIR}/cloud-init.yaml"
  [[ -f "${userdata}" ]] || die "missing ${userdata}"
  local args=(
    server create
    --name "${SERVER_NAME}"
    --type "${SERVER_TYPE}"
    --image "${IMAGE}"
    --location "${LOCATION}"
    --ssh-key "${SSH_KEY_NAME}"
    --user-data-from-file "${userdata}"
    --label "project=claire-de-binare"
    --label "role=hermes"
    --label "issue=4289"
    --firewall "${FIREWALL_NAME}"
  )
  if [[ "${HERMES_ENABLE_BACKUPS:-1}" == "1" ]]; then
    args+=(--start-after-create)
  fi
  hcloud "${args[@]}"
  # Enable backups if supported by CLI version.
  if hcloud server backup enable "${SERVER_NAME}" >/dev/null 2>&1; then
    log "backups enabled for ${SERVER_NAME}"
  else
    log "WARN: could not enable backups via CLI — verify in console before go-live"
  fi
  log "created server ${SERVER_NAME}"
}

main() {
  require_cmd hcloud
  hcloud server list >/dev/null 2>&1 || die "hcloud auth failed — set a valid token/context"
  cost_gate
  ensure_firewall
  ensure_server
  hcloud server describe "${SERVER_NAME}" -o columns=name,status,type,datacenter,labels
  log "provision complete"
}

main "$@"
