#!/usr/bin/env bash
# Idempotent Hermes host bootstrap for Hetzner (#4289).
# Fail-closed: refuses unpinned curl|bash installs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_HERMES_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIN_FILE="${HERMES_VERSION_PIN:-${REPO_HERMES_ROOT}/VERSION_PIN.yaml}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes}"
OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"
SYSTEMD_SRC="${REPO_HERMES_ROOT}/systemd"
PROFILES_SRC="${CDB_HERMES_PROFILES:-${REPO_HERMES_ROOT}/../../config/hermes/profiles}"
# Resolve relative path when run from a checkout
if [[ ! -d "${PROFILES_SRC}" ]]; then
  PROFILES_SRC="$(cd "${REPO_HERMES_ROOT}/../../config/hermes/profiles" 2>/dev/null && pwd || true)"
fi

log() { printf '[hermes-bootstrap] %s\n' "$*"; }
die() { printf '[hermes-bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

yaml_get() {
  # Minimal YAML scalar reader for our pin file (key: value).
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

assert_not_root_runtime() {
  if [[ "$(id -u)" -eq 0 ]]; then
    # Root is allowed only for package/user setup steps; Hermes runtime stays unprivileged.
    log "running privileged host setup steps as root"
  fi
}

install_systemd_units() {
  local unit_src="${SYSTEMD_SRC}/hermes-serve@.service"
  [[ -f "${unit_src}" ]] || die "missing systemd unit: ${unit_src}"
  install -m 0644 "${unit_src}" /etc/systemd/system/hermes-serve@.service
  systemctl daemon-reload
  log "installed systemd template hermes-serve@.service"
}

ensure_profile_homes() {
  local profile
  for profile in jannek-assistant cdb-engineer; do
    local home="${HERMES_BASE}/profiles/${profile}"
    mkdir -p "${home}"/{memories,sessions,skills,logs,backups}
    chown -R "${INSTALL_USER}:${INSTALL_USER}" "${home}"
    chmod 0700 "${home}"
    chmod 0700 "${home}/memories" "${home}/sessions" "${home}/logs"
    if [[ -d "${PROFILES_SRC}/${profile}" ]]; then
      # Copy distribution templates; never overwrite existing .env or memories.
      rsync -a --ignore-existing \
        --exclude '.env' \
        --exclude 'memories/' \
        --exclude 'sessions/' \
        --exclude 'state.db*' \
        --exclude 'logs/' \
        "${PROFILES_SRC}/${profile}/" "${home}/"
      chown -R "${INSTALL_USER}:${INSTALL_USER}" "${home}"
    fi
    log "profile home ready: ${profile} -> ${home}"
  done
  # validation-chief is optional and disabled until #4270.
  mkdir -p "${HERMES_BASE}/profiles/validation-chief"
  chown -R "${INSTALL_USER}:${INSTALL_USER}" "${HERMES_BASE}/profiles/validation-chief"
  chmod 0700 "${HERMES_BASE}/profiles/validation-chief"
  touch "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
  chown "${INSTALL_USER}:${INSTALL_USER}" "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
}

verify_pin() {
  [[ -f "${PIN_FILE}" ]] || die "VERSION_PIN.yaml missing: ${PIN_FILE}"
  local git_ref install_sha
  git_ref="$(yaml_get git_ref "${PIN_FILE}")"
  install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
  [[ -n "${git_ref}" ]] || die "hermes.git_ref is empty — pin a Hermes tag/commit before install"
  [[ -n "${install_sha}" ]] || die "hermes.install_script_sha256 is empty — refuse unpinned install.sh"
  log "pin ok: git_ref=${git_ref} install_script_sha256=${install_sha:0:12}..."
  printf '%s' "${git_ref}"
}

install_hermes_pinned() {
  local git_ref="$1"
  local install_url install_sha tmp sum
  install_url="$(yaml_get install_url "${PIN_FILE}")"
  install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
  [[ -n "${install_url}" ]] || die "install_url missing in pin file"
  require_cmd curl
  require_cmd sha256sum
  tmp="$(mktemp)"
  curl -fsSL "${install_url}" -o "${tmp}"
  sum="$(sha256sum "${tmp}" | awk '{print $1}')"
  [[ "${sum}" == "${install_sha}" ]] || die "install.sh sha256 mismatch (got ${sum})"
  # Install under OPT_DIR with explicit ref; do not pipe remote script blindly to bash
  # without pin verification (already done). Still run as INSTALL_USER where possible.
  mkdir -p "${OPT_DIR}"
  chown "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}"
  if [[ ! -x "${OPT_DIR}/bin/hermes" ]]; then
    log "running pinned install script (sha verified)"
    HERMES_INSTALL_DIR="${OPT_DIR}" HERMES_GIT_REF="${git_ref}" \
      sudo -u "${INSTALL_USER}" bash "${tmp}"
  else
    log "hermes binary already present; skip reinstall (idempotent)"
  fi
  rm -f "${tmp}"
  sudo -u "${INSTALL_USER}" "${OPT_DIR}/bin/hermes" --version || \
    die "hermes binary missing or broken after install"
}

enable_services() {
  systemctl enable hermes-serve@jannek-assistant.service
  systemctl enable hermes-serve@cdb-engineer.service
  # validation-chief intentionally not enabled
  systemctl restart hermes-serve@jannek-assistant.service || true
  systemctl restart hermes-serve@cdb-engineer.service || true
  log "enabled profile services (validation-chief remains disabled)"
}

main() {
  assert_not_root_runtime
  [[ "$(id -u)" -eq 0 ]] || die "bootstrap.sh must run as root on the Hetzner host"
  require_cmd rsync
  require_cmd systemctl
  local git_ref
  git_ref="$(verify_pin)"
  install_systemd_units
  ensure_profile_homes
  install_hermes_pinned "${git_ref}"
  enable_services
  log "bootstrap complete (idempotent re-run safe for homes + units)"
}

main "$@"
