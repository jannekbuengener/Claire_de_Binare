#!/usr/bin/env bash
# Destroy / revoke Hermes Hetzner host created for #4289.
# Fail-closed: only deletes resources whose names match the Hermes contract.
# Does NOT delete off-host encrypted backups. Requires CONFIRM=DESTROY.
set -euo pipefail

CONFIRM="${CONFIRM:-}"
SERVER_NAME="${HERMES_SERVER_NAME:-cdb-hermes-01}"
FIREWALL_NAME="${HERMES_FIREWALL_NAME:-cdb-hermes-deny-inbound}"
ALLOWED_SERVER_NAME="cdb-hermes-01"
ALLOWED_FIREWALL_NAME="cdb-hermes-deny-inbound"

die() { printf '[hermes-destroy] ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[hermes-destroy] %s\n' "$*"; }

[[ "${CONFIRM}" == "DESTROY" ]] || die "set CONFIRM=DESTROY to proceed"
[[ "${SERVER_NAME}" == "${ALLOWED_SERVER_NAME}" ]] \
  || die "refuse destroy of unexpected server name: ${SERVER_NAME}"
[[ "${FIREWALL_NAME}" == "${ALLOWED_FIREWALL_NAME}" ]] \
  || die "refuse destroy of unexpected firewall name: ${FIREWALL_NAME}"

command -v hcloud >/dev/null 2>&1 || die "hcloud CLI required"

# Label / name guard: if server exists, require matching name only (no wildcards).
if hcloud server describe "${SERVER_NAME}" >/dev/null 2>&1; then
  labels="$(hcloud server describe "${SERVER_NAME}" -o json 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("labels") or {})' \
    2>/dev/null || echo '{}')"
  log "target server labels=${labels}"
else
  log "server ${SERVER_NAME} already absent"
fi

# Best-effort local stop if executed on the host itself.
if command -v systemctl >/dev/null 2>&1; then
  systemctl stop 'hermes-dashboard@*' 2>/dev/null || true
  systemctl disable 'hermes-dashboard@*' 2>/dev/null || true
  systemctl stop 'hermes-serve@*' 2>/dev/null || true
  systemctl disable 'hermes-serve@*' 2>/dev/null || true
fi

if hcloud server describe "${SERVER_NAME}" >/dev/null 2>&1; then
  hcloud server delete "${SERVER_NAME}"
  log "deleted server ${SERVER_NAME}"
else
  log "server ${SERVER_NAME} already absent"
fi

if hcloud firewall describe "${FIREWALL_NAME}" >/dev/null 2>&1; then
  hcloud firewall delete "${FIREWALL_NAME}"
  log "deleted firewall ${FIREWALL_NAME}"
else
  log "firewall ${FIREWALL_NAME} already absent"
fi

cat <<'EOF'
Revocation checklist (manual / Human-GO):
  1. Revoke Tailscale device auth for this host.
  2. Rotate/revoke GitHub App installation tokens and any profile PATs.
  3. Disable Windows OpenSSH for the dedicated Hermes user / kill-switch ON.
  4. Wipe or re-key off-host encrypted Hermes backups if decommissioning.
  5. Confirm no public ports remain on residual floating IPs.
EOF
