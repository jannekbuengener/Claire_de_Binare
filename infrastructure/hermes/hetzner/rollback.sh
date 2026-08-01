#!/usr/bin/env bash
# Rollback Hermes install to previously recorded commit (#4289).
set -euo pipefail

INSTALL_DIR="${HERMES_INSTALL_DIR:-/opt/hermes}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
PREV_MARKER="/var/lib/hermes/.previous_install_commit"

log() { printf '[hermes-rollback] %s\n' "$*"; }
die() { printf '[hermes-rollback] ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "rollback.sh must run as root"
[[ "${CONFIRM:-}" == "ROLLBACK" ]] || die "set CONFIRM=ROLLBACK"
[[ -f "${PREV_MARKER}" ]] || die "missing ${PREV_MARKER} (no update marker)"
prev="$(tr -d '[:space:]' < "${PREV_MARKER}")"
[[ -n "${prev}" ]] || die "empty previous commit marker"

systemctl stop 'hermes-dashboard@*' 2>/dev/null || true

INSTALLER="$(mktemp)"
trap 'rm -f "${INSTALLER}"' EXIT
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o "${INSTALLER}"
EXPECTED_SHA="${HERMES_INSTALL_SH_SHA256:-}"
if [[ -n "${EXPECTED_SHA}" ]]; then
  got="$(sha256sum "${INSTALLER}" | awk '{print $1}')"
  [[ "${got}" == "${EXPECTED_SHA}" ]] || die "install.sh sha256 mismatch"
fi

sudo -u "${INSTALL_USER}" bash "${INSTALLER}" \
  --non-interactive --skip-browser \
  --dir "${INSTALL_DIR}" \
  --commit "${prev}" \
  --hermes-home /var/lib/hermes/profiles/jannek-assistant

chown -R "${INSTALL_USER}:${INSTALL_USER}" "${INSTALL_DIR}"
systemctl start hermes-dashboard@jannek-assistant.service
systemctl start hermes-dashboard@cdb-engineer.service
systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
  || die "post-rollback start failed"
log "rolled back to ${prev}"
