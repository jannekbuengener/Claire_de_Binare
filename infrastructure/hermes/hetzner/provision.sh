#!/usr/bin/env bash
# Idempotent Hetzner Cloud provisioner for Hermes (#4289).
# Applies firewall + server via hcloud CLI. server.yaml / firewall.yaml are
# intent mirrors (documented defaults); live apply uses the variables below
# which must stay aligned with those YAML files.
# Fail-closed on cost / duplicates / backup enable failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_NAME="${HERMES_SERVER_NAME:-cdb-hermes-01}"
FIREWALL_NAME="${HERMES_FIREWALL_NAME:-cdb-hermes-deny-inbound}"
LOCATION="${HERMES_LOCATION:-fsn1}"
SERVER_TYPE="${HERMES_SERVER_TYPE:-cx23}"
IMAGE="${HERMES_IMAGE:-ubuntu-24.04}"
SSH_KEY_NAME="${HERMES_SSH_KEY_NAME:-}"
MONTHLY_LIMIT_EUR="${HERMES_MONTHLY_EUR_LIMIT:-15}"
# Documented estimate (live price table 2026-08-02): CX23 ~6.53 + IPv4 0.50 + backups ~20%
# CPX21 remains compatible but is no longer orderable in EU locations.
ESTIMATE_EUR="${HERMES_COST_ESTIMATE_EUR:-9.03}"
ENABLE_BACKUPS="${HERMES_ENABLE_BACKUPS:-1}"

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
  # Default deny inbound (matches firewall.yaml intent: inbound: []).
  # Optional short-lived admin SSH exception for first bootstrap only.
  # Set HERMES_BOOTSTRAP_ADMIN_CIDR=x.x.x.x/32 then remove after Tailscale.
  if [[ -n "${HERMES_BOOTSTRAP_ADMIN_CIDR:-}" ]]; then
    if hcloud firewall describe "${FIREWALL_NAME}" -o json \
      | grep -q "hermes-bootstrap-ssh-temp"; then
      log "temp SSH rule already present for ${FIREWALL_NAME}"
    else
      hcloud firewall add-rule \
        --direction in \
        --protocol tcp \
        --port 22 \
        --source-ips "${HERMES_BOOTSTRAP_ADMIN_CIDR}" \
        --description "hermes-bootstrap-ssh-temp" \
        "${FIREWALL_NAME}"
      log "added temp SSH allow from ${HERMES_BOOTSTRAP_ADMIN_CIDR} (remove after Tailscale)"
    fi
  else
    log "firewall inbound remains deny-by-default (no public Hermes/SSH ports)"
  fi
}

enable_backups_or_die() {
  if [[ "${ENABLE_BACKUPS}" != "1" ]]; then
    die "HERMES_ENABLE_BACKUPS must be 1 for #4289 (backups required under cost gate)"
  fi
  if hcloud server backup enable "${SERVER_NAME}"; then
    log "backups enabled for ${SERVER_NAME}"
  else
    die "failed to enable backups for ${SERVER_NAME} — refuse incomplete provision"
  fi
}

ensure_server() {
  if hcloud server describe "${SERVER_NAME}" >/dev/null 2>&1; then
    log "server already exists: ${SERVER_NAME} (no duplicate create)"
    # Idempotent: ensure backups are on for pre-existing session-owned host.
    enable_backups_or_die
    return 0
  fi
  [[ -n "${SSH_KEY_NAME}" ]] || die "set HERMES_SSH_KEY_NAME to an existing hcloud SSH key"
  local userdata="${SCRIPT_DIR}/cloud-init.yaml"
  [[ -f "${userdata}" ]] || die "missing ${userdata}"
  # Align with server.yaml intent (name/type/image/location/labels/firewall).
  hcloud server create \
    --name "${SERVER_NAME}" \
    --type "${SERVER_TYPE}" \
    --image "${IMAGE}" \
    --location "${LOCATION}" \
    --ssh-key "${SSH_KEY_NAME}" \
    --user-data-from-file "${userdata}" \
    --label "project=claire-de-binare" \
    --label "role=hermes" \
    --label "issue=4289" \
    --firewall "${FIREWALL_NAME}"
  enable_backups_or_die
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
