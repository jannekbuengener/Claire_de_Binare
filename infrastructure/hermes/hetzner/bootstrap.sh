#!/usr/bin/env bash
# Idempotent Hermes host bootstrap for Hetzner (#4289).
# Fail-closed: refuses unpinned installs; fails on service start errors.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_HERMES_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIN_FILE="${HERMES_VERSION_PIN:-${REPO_HERMES_ROOT}/VERSION_PIN.yaml}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes}"
OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"
SYSTEMD_SRC="${REPO_HERMES_ROOT}/systemd"
ENV_SRC="${SYSTEMD_SRC}/env"
PROFILES_SRC="${CDB_HERMES_PROFILES:-${REPO_HERMES_ROOT}/../../config/hermes/profiles}"
if [[ ! -d "${PROFILES_SRC}" ]]; then
  PROFILES_SRC="$(cd "${REPO_HERMES_ROOT}/../../config/hermes/profiles" 2>/dev/null && pwd || true)"
fi

log() { printf '[hermes-bootstrap] %s\n' "$*"; }
die() { printf '[hermes-bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

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

install_systemd_units() {
  local unit_src="${SYSTEMD_SRC}/hermes-dashboard@.service"
  [[ -f "${unit_src}" ]] || die "missing systemd unit: ${unit_src}"
  install -m 0644 "${unit_src}" /etc/systemd/system/hermes-dashboard@.service
  # Remove legacy misnamed unit if present (hermes serve is not official).
  rm -f /etc/systemd/system/hermes-serve@.service
  systemctl daemon-reload
  log "installed systemd template hermes-dashboard@.service"
}

install_profile_env_files() {
  mkdir -p /etc/hermes
  chmod 0750 /etc/hermes
  local profile port
  declare -A PORTS=(
    [jannek-assistant]=9119
    [cdb-engineer]=9120
  )
  for profile in "${!PORTS[@]}"; do
    local dest="/etc/hermes/${profile}.env"
    if [[ ! -f "${dest}" ]]; then
      if [[ -f "${ENV_SRC}/${profile}.env.example" ]]; then
        install -m 0640 "${ENV_SRC}/${profile}.env.example" "${dest}"
      else
        printf 'HERMES_PORT=%s\n' "${PORTS[$profile]}" >"${dest}"
        chmod 0640 "${dest}"
      fi
      chown root:"${INSTALL_USER}" "${dest}"
      log "created ${dest}"
    else
      # Ensure HERMES_PORT present for concurrent profiles.
      if ! grep -q '^HERMES_PORT=' "${dest}"; then
        die "${dest} missing HERMES_PORT — refuse ambiguous bind"
      fi
      log "env present: ${dest}"
    fi
  done
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
      rsync -a --ignore-existing \
        --exclude '.env' \
        --exclude 'memories/' \
        --exclude 'sessions/' \
        --exclude 'state.db*' \
        --exclude 'logs/' \
        "${PROFILES_SRC}/${profile}/" "${home}/"
      chown -R "${INSTALL_USER}:${INSTALL_USER}" "${home}"
    fi
    # Sync port into profile config.yaml server.port if present.
    log "profile home ready: ${profile} -> ${home}"
  done
  mkdir -p "${HERMES_BASE}/profiles/validation-chief"
  chown -R "${INSTALL_USER}:${INSTALL_USER}" "${HERMES_BASE}/profiles/validation-chief"
  chmod 0700 "${HERMES_BASE}/profiles/validation-chief"
  touch "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
  chown "${INSTALL_USER}:${INSTALL_USER}" "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
}

verify_pin() {
  [[ -f "${PIN_FILE}" ]] || die "VERSION_PIN.yaml missing: ${PIN_FILE}"
  local git_ref git_commit install_sha
  git_ref="$(yaml_get git_ref "${PIN_FILE}")"
  git_commit="$(yaml_get git_commit "${PIN_FILE}")"
  install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
  [[ -n "${git_ref}" ]] || die "hermes.git_ref is empty — pin a Hermes tag before install"
  [[ -n "${git_commit}" ]] || die "hermes.git_commit is empty — pin exact commit before install"
  [[ -n "${install_sha}" ]] || die "hermes.install_script_sha256 is empty — refuse unpinned install.sh"
  log "pin ok: ref=${git_ref} commit=${git_commit:0:12} sha256=${install_sha:0:12}..."
  printf '%s %s' "${git_ref}" "${git_commit}"
}

install_hermes_pinned() {
  local git_ref="$1"
  local git_commit="$2"
  local install_url install_sha tmp sum code_dir bin_link
  install_url="$(yaml_get install_url "${PIN_FILE}")"
  install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
  [[ -n "${install_url}" ]] || die "install_url missing in pin file"
  require_cmd curl
  require_cmd sha256sum
  require_cmd git
  tmp="$(mktemp)"
  curl -fsSL "${install_url}" -o "${tmp}"
  sum="$(sha256sum "${tmp}" | awk '{print $1}')"
  [[ "${sum}" == "${install_sha}" ]] || die "install.sh sha256 mismatch (got ${sum})"
  # Official installer supports --dir/--hermes-home/--branch/--commit (NOT HERMES_GIT_REF).
  code_dir="${OPT_DIR}/hermes-agent"
  mkdir -p "${OPT_DIR}/bin" /var/lib/hermes/_installer_home
  chown -R "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}" /var/lib/hermes/_installer_home
  if [[ ! -x "${OPT_DIR}/bin/hermes" ]]; then
    log "running pinned install.sh --branch ${git_ref} --commit ${git_commit}"
    sudo -u "${INSTALL_USER}" bash "${tmp}" \
      --dir "${code_dir}" \
      --hermes-home /var/lib/hermes/_installer_home \
      --branch "${git_ref}" \
      --commit "${git_commit}" \
      --skip-browser \
      --non-interactive \
      --skip-setup
  else
    log "hermes binary already present; verifying checkout pin"
  fi
  rm -f "${tmp}"
  # Prefer venv launcher from the pinned checkout.
  if [[ -x "${code_dir}/venv/bin/hermes" ]]; then
    ln -sfn "${code_dir}/venv/bin/hermes" "${OPT_DIR}/bin/hermes"
  elif [[ -x "${code_dir}/hermes" ]]; then
    die "found source hermes wrapper without venv launcher — refuse unsafe PATH"
  fi
  # Verify commit when .git exists.
  if [[ -d "${code_dir}/.git" ]]; then
    local head
    head="$(git -C "${code_dir}" rev-parse HEAD)"
    [[ "${head}" == "${git_commit}" ]] || die "checkout HEAD ${head} != pinned ${git_commit}"
  fi
  sudo -u "${INSTALL_USER}" "${OPT_DIR}/bin/hermes" --version || \
    die "hermes binary missing or broken after install"
}

enable_services() {
  systemctl enable hermes-dashboard@jannek-assistant.service
  systemctl enable hermes-dashboard@cdb-engineer.service
  systemctl restart hermes-dashboard@jannek-assistant.service
  systemctl restart hermes-dashboard@cdb-engineer.service
  systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
    || die "jannek-assistant dashboard failed to start"
  systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
    || die "cdb-engineer dashboard failed to start"
  # Port conflict probe: both must listen on distinct loopback ports.
  local p1 p2
  p1="$(grep -E '^HERMES_PORT=' /etc/hermes/jannek-assistant.env | cut -d= -f2)"
  p2="$(grep -E '^HERMES_PORT=' /etc/hermes/cdb-engineer.env | cut -d= -f2)"
  [[ -n "${p1}" && -n "${p2}" && "${p1}" != "${p2}" ]] \
    || die "profile ports must be distinct (got ${p1:-empty} vs ${p2:-empty})"
  log "enabled profile dashboards on ports ${p1} and ${p2}"
}

main() {
  [[ "$(id -u)" -eq 0 ]] || die "bootstrap.sh must run as root on the Hetzner host"
  require_cmd rsync
  require_cmd systemctl
  local pin_pair git_ref git_commit
  pin_pair="$(verify_pin)"
  git_ref="${pin_pair%% *}"
  git_commit="${pin_pair##* }"
  install_systemd_units
  install_profile_env_files
  ensure_profile_homes
  install_hermes_pinned "${git_ref}" "${git_commit}"
  enable_services
  log "bootstrap complete (idempotent re-run safe for homes + units)"
}

main "$@"
