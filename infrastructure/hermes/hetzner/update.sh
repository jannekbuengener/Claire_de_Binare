#!/usr/bin/env bash
# Controlled Hermes update with rollback marker (#4289).
# Downloads only the pinned install.sh URL and requires sha256 match.
# Checkout path matches bootstrap.sh: /opt/hermes/hermes-agent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIN_FILE="${HERMES_VERSION_PIN:-${SCRIPT_DIR}/../VERSION_PIN.yaml}"
OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"
CODE_DIR="${HERMES_CODE_DIR:-${OPT_DIR}/hermes-agent}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
PREV_MARKER="/var/lib/hermes/.previous_install_commit"

log() { printf '[hermes-update] %s\n' "$*"; }
die() { printf '[hermes-update] ERROR: %s\n' "$*" >&2; exit 1; }

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

[[ "$(id -u)" -eq 0 ]] || die "update.sh must run as root"
[[ "${CONFIRM:-}" == "UPDATE" ]] || die "set CONFIRM=UPDATE"
[[ -f "${PIN_FILE}" ]] || die "VERSION_PIN.yaml missing: ${PIN_FILE}"

install_url="$(yaml_get install_url "${PIN_FILE}")"
install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
git_ref="$(yaml_get git_ref "${PIN_FILE}")"
git_commit="$(yaml_get git_commit "${PIN_FILE}")"
[[ -n "${install_url}" ]] || die "hermes.install_url empty in pin"
[[ -n "${install_sha}" ]] || die "hermes.install_script_sha256 empty — refuse unpinned install.sh"
[[ -n "${git_ref}" ]] || die "hermes.git_ref empty in pin"
[[ -n "${git_commit}" ]] || die "hermes.git_commit empty in pin"
# Optional overrides must still be non-empty when set; default to pin.
TARGET_COMMIT="${HERMES_COMMIT:-${git_commit}}"
TARGET_BRANCH="${HERMES_GIT_REF:-${git_ref}}"
[[ -n "${TARGET_COMMIT}" ]] || die "TARGET_COMMIT empty"
[[ -n "${TARGET_BRANCH}" ]] || die "TARGET_BRANCH empty"

mkdir -p /var/lib/hermes
if [[ -d "${CODE_DIR}/.git" ]]; then
  prev="$(git -C "${CODE_DIR}" rev-parse HEAD)"
  printf '%s\n' "${prev}" > "${PREV_MARKER}"
  chmod 0600 "${PREV_MARKER}"
  log "previous commit recorded: ${prev}"
else
  die "missing git checkout at ${CODE_DIR} — refuse update without rollback baseline"
fi

systemctl stop 'hermes-dashboard@*' 2>/dev/null || true

INSTALLER="$(mktemp)"
trap 'rm -f "${INSTALLER}"' EXIT
# Never curl unsigned main/scripts/install.sh — only the pin URL.
curl -fsSL "${install_url}" -o "${INSTALLER}"
got="$(sha256sum "${INSTALLER}" | awk '{print $1}')"
[[ "${got}" == "${install_sha}" ]] || die "install.sh sha256 mismatch: got=${got} expected=${install_sha}"

sudo -u "${INSTALL_USER}" bash "${INSTALLER}" \
  --non-interactive \
  --skip-browser \
  --skip-setup \
  --dir "${CODE_DIR}" \
  --hermes-home /var/lib/hermes/_installer_home \
  --branch "${TARGET_BRANCH}" \
  --commit "${TARGET_COMMIT}"

if [[ -d "${CODE_DIR}/.git" ]]; then
  head="$(git -C "${CODE_DIR}" rev-parse HEAD)"
  [[ "${head}" == "${TARGET_COMMIT}" ]] || die "checkout HEAD ${head} != target ${TARGET_COMMIT}"
fi

if [[ -x "${CODE_DIR}/venv/bin/hermes" ]]; then
  mkdir -p "${OPT_DIR}/bin"
  ln -sfn "${CODE_DIR}/venv/bin/hermes" "${OPT_DIR}/bin/hermes"
else
  die "missing ${CODE_DIR}/venv/bin/hermes after update"
fi
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}" /var/lib/hermes/_installer_home

systemctl start hermes-dashboard@jannek-assistant.service
systemctl start hermes-dashboard@cdb-engineer.service
systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
  || die "post-update start failed: jannek-assistant"
systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
  || die "post-update start failed: cdb-engineer"

log "update complete; rollback via rollback.sh if needed"
