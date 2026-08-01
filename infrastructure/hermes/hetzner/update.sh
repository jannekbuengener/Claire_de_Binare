#!/usr/bin/env bash
# Controlled Hermes update with rollback marker (#4289).
# Pins via infrastructure/hermes/VERSION_PIN.yaml (passed as env or args).
set -euo pipefail

INSTALL_DIR="${HERMES_INSTALL_DIR:-/opt/hermes}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
TARGET_COMMIT="${HERMES_COMMIT:-}"
TARGET_BRANCH="${HERMES_GIT_REF:-}"
PREV_MARKER="/var/lib/hermes/.previous_install_commit"

log() { printf '[hermes-update] %s\n' "$*"; }
die() { printf '[hermes-update] ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "update.sh must run as root"
[[ -n "${TARGET_COMMIT}" || -n "${TARGET_BRANCH}" ]] || die "set HERMES_COMMIT or HERMES_GIT_REF"
[[ "${CONFIRM:-}" == "UPDATE" ]] || die "set CONFIRM=UPDATE"

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  prev="$(git -C "${INSTALL_DIR}" rev-parse HEAD)"
  printf '%s\n' "${prev}" > "${PREV_MARKER}"
  chmod 0600 "${PREV_MARKER}"
  log "previous commit recorded: ${prev}"
fi

systemctl stop 'hermes-dashboard@*' 2>/dev/null || true

INSTALLER="$(mktemp)"
trap 'rm -f "${INSTALLER}"' EXIT
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o "${INSTALLER}"
EXPECTED_SHA="${HERMES_INSTALL_SH_SHA256:-}"
if [[ -n "${EXPECTED_SHA}" ]]; then
  got="$(sha256sum "${INSTALLER}" | awk '{print $1}')"
  [[ "${got}" == "${EXPECTED_SHA}" ]] || die "install.sh sha256 mismatch: got=${got}"
fi

args=(--non-interactive --skip-browser --dir "${INSTALL_DIR}" --hermes-home /var/lib/hermes/profiles/jannek-assistant)
if [[ -n "${TARGET_COMMIT}" ]]; then
  args+=(--commit "${TARGET_COMMIT}")
else
  args+=(--branch "${TARGET_BRANCH}")
fi

sudo -u "${INSTALL_USER}" bash "${INSTALLER}" "${args[@]}"
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${INSTALL_DIR}"

systemctl start hermes-dashboard@jannek-assistant.service
systemctl start hermes-dashboard@cdb-engineer.service
systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
  || die "post-update start failed: jannek-assistant"
systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
  || die "post-update start failed: cdb-engineer"

log "update complete; rollback via rollback.sh if needed"
