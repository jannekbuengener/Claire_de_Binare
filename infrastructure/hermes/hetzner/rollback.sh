#!/usr/bin/env bash
# Rollback Hermes install to previously recorded commit (#4289).
# Uses pinned install.sh URL + required sha256 (never main/scripts/install.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIN_FILE="${HERMES_VERSION_PIN:-${SCRIPT_DIR}/../VERSION_PIN.yaml}"
OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"
CODE_DIR="${HERMES_CODE_DIR:-${OPT_DIR}/hermes-agent}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
PREV_MARKER="/var/lib/hermes/.previous_install_commit"

log() { printf '[hermes-rollback] %s\n' "$*"; }
die() { printf '[hermes-rollback] ERROR: %s\n' "$*" >&2; exit 1; }

yaml_get() {
  local key="$1"
  local file="$2"
  awk -v k="$key" '
    $0 ~ "^[[:space:]]*"k":" {
      sub(/^[^:]+:[[:space:]]*/, "", $0)
      gsub(/"/, "", $0)
      print $0
      exit
    }
  ' "$file"
}

[[ "$(id -u)" -eq 0 ]] || die "rollback.sh must run as root"
[[ "${CONFIRM:-}" == "ROLLBACK" ]] || die "set CONFIRM=ROLLBACK"
[[ -f "${PREV_MARKER}" ]] || die "missing ${PREV_MARKER} (no update marker)"
[[ -f "${PIN_FILE}" ]] || die "VERSION_PIN.yaml missing: ${PIN_FILE}"

prev="$(tr -d '[:space:]' < "${PREV_MARKER}")"
[[ -n "${prev}" ]] || die "empty previous commit marker"

install_url="$(yaml_get install_url "${PIN_FILE}")"
install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
git_ref="$(yaml_get git_ref "${PIN_FILE}")"
[[ -n "${install_url}" ]] || die "hermes.install_url empty in pin"
[[ -n "${install_sha}" ]] || die "hermes.install_script_sha256 empty — refuse unpinned install.sh"
[[ -n "${git_ref}" ]] || die "hermes.git_ref empty in pin"

systemctl stop 'hermes-dashboard@*' 2>/dev/null || true

INSTALLER="$(mktemp)"
trap 'rm -f "${INSTALLER}"' EXIT
curl -fsSL "${install_url}" -o "${INSTALLER}"
got="$(sha256sum "${INSTALLER}" | awk '{print $1}')"
[[ "${got}" == "${install_sha}" ]] || die "install.sh sha256 mismatch: got=${got}"

sudo -u "${INSTALL_USER}" bash "${INSTALLER}" \
  --non-interactive \
  --skip-browser \
  --skip-setup \
  --dir "${CODE_DIR}" \
  --hermes-home /var/lib/hermes/_installer_home \
  --branch "${git_ref}" \
  --commit "${prev}" \
  --force-commit

if [[ -d "${CODE_DIR}/.git" ]]; then
  head="$(git -C "${CODE_DIR}" rev-parse HEAD)"
  [[ "${head}" == "${prev}" ]] || die "rollback HEAD ${head} != previous ${prev}"
fi

if [[ -x "${CODE_DIR}/venv/bin/hermes" ]]; then
  mkdir -p "${OPT_DIR}/bin"
  ln -sfn "${CODE_DIR}/venv/bin/hermes" "${OPT_DIR}/bin/hermes"
else
  die "missing ${CODE_DIR}/venv/bin/hermes after rollback"
fi
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}" /var/lib/hermes/_installer_home

systemctl start hermes-dashboard@jannek-assistant.service
systemctl start hermes-dashboard@cdb-engineer.service
systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
  || die "post-rollback start failed: jannek-assistant"
systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
  || die "post-rollback start failed: cdb-engineer"
log "rolled back to ${prev}"
