#!/usr/bin/env bash
# Idempotent Hermes host bootstrap for Hetzner (#4289 / #4329).
# Fail-closed: refuses unpinned installs; fails on service start errors.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_HERMES_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIN_FILE="${HERMES_VERSION_PIN:-${REPO_HERMES_ROOT}/VERSION_PIN.yaml}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"
declare -A PROFILE_LINUX_USERS=(
  [jannek-assistant]=hermes-jannek-assistant
  [cdb-engineer]=hermes-cdb-engineer
)
HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes}"
OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"
INSTALLER_HOME="${HERMES_INSTALLER_HOME:-/var/lib/hermes/_installer_home}"
LOG_BASE="${HERMES_LOG_DIR:-/var/log/hermes}"
SYSTEMD_SRC="${REPO_HERMES_ROOT}/systemd"
ENV_SRC="${SYSTEMD_SRC}/env"
PROFILES_SRC="${CDB_HERMES_PROFILES:-${REPO_HERMES_ROOT}/../../config/hermes/profiles}"
if [[ ! -d "${PROFILES_SRC}" ]]; then
  PROFILES_SRC="$(cd "${REPO_HERMES_ROOT}/../../config/hermes/profiles" 2>/dev/null && pwd || true)"
fi

# Progress/status logs MUST go to stderr so command-substitution callers
# (e.g. pin_pair="$(verify_pin)") only capture machine values on stdout (#4329).
log() { printf '[hermes-bootstrap] %s\n' "$*" >&2; }
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

ensure_profile_linux_users() {
  local profile user
  for profile in jannek-assistant cdb-engineer; do
    user="${PROFILE_LINUX_USERS[${profile}]}"
    if ! id -u "${user}" >/dev/null 2>&1; then
      useradd --system --user-group --create-home=no --shell /usr/sbin/nologin "${user}" \
        || die "failed to create ${user}"
      log "created system user ${user}"
    fi
  done
}

install_systemd_units() {
  local unit_src="${SYSTEMD_SRC}/hermes-dashboard@.service"
  local broker_src="${SYSTEMD_SRC}/hermes-github-token.service"
  local gateway_src="${SYSTEMD_SRC}/hermes-gateway-cdb-engineer.service"
  local transport_src="${SYSTEMD_SRC}/hermes-runs-tailnet-transport.service"
  [[ -f "${unit_src}" ]] || die "missing systemd unit: ${unit_src}"
  [[ -f "${gateway_src}" ]] || die "missing systemd unit: ${gateway_src}"
  [[ -f "${transport_src}" ]] || die "missing systemd unit: ${transport_src}"
  install -m 0644 "${unit_src}" /etc/systemd/system/hermes-dashboard@.service
  install -m 0644 "${gateway_src}" /etc/systemd/system/hermes-gateway-cdb-engineer.service
  install -m 0644 "${transport_src}" /etc/systemd/system/hermes-runs-tailnet-transport.service
  if [[ -f "${broker_src}" ]]; then
    install -m 0644 "${broker_src}" /etc/systemd/system/hermes-github-token.service
  fi
  # Remove legacy misnamed unit if present (hermes serve is not official).
  rm -f /etc/systemd/system/hermes-serve@.service
  systemctl daemon-reload
  log "installed systemd template hermes-dashboard@.service (+ broker if present)"
}

install_profile_env_files() {
  mkdir -p /etc/hermes
  chmod 0751 /etc/hermes
  # Directory root-owned; each env file is root:profile-user 0640 (B2.0).
  # No shared hermes group mediates cross-profile secret/env access.
  chown root:root /etc/hermes
  local profile port user
  declare -A PORTS=(
    [jannek-assistant]=9119
    [cdb-engineer]=9120
  )
  for profile in "${!PORTS[@]}"; do
    user="${PROFILE_LINUX_USERS[${profile}]}"
    local dest="/etc/hermes/${profile}.env"
    if [[ ! -f "${dest}" ]]; then
      if [[ -f "${ENV_SRC}/${profile}.env.example" ]]; then
        install -m 0640 "${ENV_SRC}/${profile}.env.example" "${dest}"
      else
        printf 'HERMES_PORT=%s\n' "${PORTS[$profile]}" >"${dest}"
        chmod 0640 "${dest}"
      fi
      chown "root:${user}" "${dest}"
      log "created ${dest}"
    else
      # Ensure HERMES_PORT present for concurrent profiles.
      if ! grep -q '^HERMES_PORT=' "${dest}"; then
        die "${dest} missing HERMES_PORT — refuse ambiguous bind"
      fi
      chown "root:${user}" "${dest}"
      chmod 0640 "${dest}"
      log "env present: ${dest}"
    fi
  done
}

# Parent/opt/home traverse for dedicated profile UIDs (B2.0 live cutover).
# Profiles stay 0700; parents must be 0751 so systemd WorkingDirectory/ENV work.
# Mirrors migrate-profile-uids.sh migrate_ownership — idempotent.
apply_dedicated_uid_traverse_perms() {
  mkdir -p "${HERMES_BASE}" "${LOG_BASE}"
  chmod 0751 "${HERMES_BASE}"
  chmod 0751 "${LOG_BASE}"
  if [[ -d /etc/hermes ]]; then
    chmod 0751 /etc/hermes
  fi
  # Shared install tree may remain under hermes (binary only — no tokens/PEM).
  # Profile UIDs must execute the binary (o+rx); never share secrets here.
  if [[ -d "${OPT_DIR}" ]]; then
    if id -u "${INSTALL_USER}" >/dev/null 2>&1; then
      chown -R "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}"
    fi
    chmod 0755 "${OPT_DIR}"
    find "${OPT_DIR}" -type d -exec chmod a+rx {} +
    find "${OPT_DIR}" -type f -executable -exec chmod a+rx {} +
  fi
  # uv-managed interpreter path used with ProtectHome=read-only (#4329).
  if [[ -d /home/hermes ]]; then
    chmod 0751 /home/hermes
  fi
  if [[ -d /home/hermes/.local/share/uv ]]; then
    chmod -R a+rX /home/hermes/.local/share/uv
  fi
  if [[ -d "${INSTALLER_HOME}" ]]; then
    chmod -R a+rX "${INSTALLER_HOME}"
  fi
  log "dedicated-UID traverse perms applied (parents 0751, opt execute, uv read)"
}

ensure_profile_homes() {
  local profile user home logdir
  mkdir -p "${HERMES_BASE}" "${LOG_BASE}"
  chmod 0751 "${HERMES_BASE}"
  chmod 0751 "${LOG_BASE}"
  for profile in jannek-assistant cdb-engineer; do
    user="${PROFILE_LINUX_USERS[${profile}]}"
    home="${HERMES_BASE}/profiles/${profile}"
    logdir="${LOG_BASE}/${profile}"
    mkdir -p "${home}"/{memories,sessions,skills,logs,backups}
    mkdir -p "${logdir}"
    chown -R "${user}:${user}" "${home}" "${logdir}"
    chmod 0700 "${home}"
    chmod 0700 "${home}/memories" "${home}/sessions" "${home}/logs"
    chmod 0700 "${logdir}"
    if [[ -d "${PROFILES_SRC}/${profile}" ]]; then
      rsync -a --ignore-existing \
        --exclude '.env' \
        --exclude 'memories/' \
        --exclude 'sessions/' \
        --exclude 'state.db*' \
        --exclude 'logs/' \
        "${PROFILES_SRC}/${profile}/" "${home}/"
      chown -R "${user}:${user}" "${home}"
    fi
    log "profile home ready: ${profile} -> ${home} (uid ${user})"
  done
  mkdir -p "${HERMES_BASE}/profiles/validation-chief"
  chmod 0700 "${HERMES_BASE}/profiles/validation-chief"
  touch "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
  chown root:root "${HERMES_BASE}/profiles/validation-chief" \
    "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
  apply_dedicated_uid_traverse_perms
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
  local install_url install_sha tmp sum code_dir
  install_url="$(yaml_get install_url "${PIN_FILE}")"
  install_sha="$(yaml_get install_script_sha256 "${PIN_FILE}")"
  [[ -n "${install_url}" ]] || die "install_url missing in pin file"
  require_cmd curl
  require_cmd sha256sum
  require_cmd git
  tmp="$(mktemp)"
  # Always remove the temp installer — success or fail (#4329).
  _cleanup_install_tmp() { rm -f "${tmp}"; }
  trap _cleanup_install_tmp EXIT
  curl -fsSL "${install_url}" -o "${tmp}"
  sum="$(sha256sum "${tmp}" | awk '{print $1}')"
  [[ "${sum}" == "${install_sha}" ]] || die "install.sh sha256 mismatch (got ${sum})"
  # mktemp defaults to 0600 root:root; hermes must read it under sudo -u (#4329).
  # Mode 0644 = readable, not writable, by INSTALL_USER.
  chmod 0644 "${tmp}"
  # Official installer supports --dir/--hermes-home/--branch/--commit (NOT HERMES_GIT_REF).
  code_dir="${OPT_DIR}/hermes-agent"
  mkdir -p "${OPT_DIR}/bin" "${INSTALLER_HOME}"
  chown -R "${INSTALL_USER}:${INSTALL_USER}" "${OPT_DIR}" "${INSTALLER_HOME}"
  if [[ ! -x "${OPT_DIR}/bin/hermes" ]]; then
    log "running pinned install.sh --branch ${git_ref} --commit ${git_commit}"
    sudo -u "${INSTALL_USER}" bash "${tmp}" \
      --dir "${code_dir}" \
      --hermes-home "${INSTALLER_HOME}" \
      --branch "${git_ref}" \
      --commit "${git_commit}" \
      --skip-browser \
      --non-interactive \
      --skip-setup
  else
    log "hermes binary already present; verifying checkout pin"
  fi
  _cleanup_install_tmp
  trap - EXIT
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

ensure_dashboard_runtime_assets() {
  # After pinned install: managed Node from installer home, web_dist, per-profile
  # stamps. Uses only the installer-provided Node tree — no floating nodejs.org
  # latest download (#4329 / host evidence from #4327).
  local code_dir="${OPT_DIR}/hermes-agent"
  local node_root="${INSTALLER_HOME}/node"
  local node_bin="${node_root}/bin"
  local dist_index="${code_dir}/hermes_cli/web_dist/index.html"
  local profile home

  [[ -x "${OPT_DIR}/bin/hermes" ]] || die "hermes binary missing before dashboard asset prep"
  [[ -d "${code_dir}" ]] || die "hermes checkout missing: ${code_dir}"
  [[ -x "${node_bin}/node" ]] || die "managed node missing at ${node_bin}/node — refuse floating Node install"
  [[ -x "${node_bin}/npm" ]] || die "managed npm missing at ${node_bin}/npm"

  if [[ ! -f "${dist_index}" ]]; then
    log "building web UI into hermes_cli/web_dist (index.html missing)"
    [[ -f "${code_dir}/web/package.json" ]] || die "web/package.json missing — cannot build dashboard UI"
    sudo -u "${INSTALL_USER}" env PATH="${node_bin}:${PATH}" \
      bash -lc "cd '${code_dir}/web' && npm install --no-fund --no-audit && npm run build"
    [[ -f "${dist_index}" ]] || die "web UI build failed — ${dist_index} still missing"
  else
    log "web UI dist present: hermes_cli/web_dist/index.html"
  fi

  for profile in jannek-assistant cdb-engineer; do
    local user="${PROFILE_LINUX_USERS[${profile}]}"
    home="${HERMES_BASE}/profiles/${profile}"
    [[ -d "${home}" ]] || die "profile home missing: ${home}"
    # Hermes resolves managed Node under \$HERMES_HOME/node.
    ln -sfn "${node_root}" "${home}/node"
    chown -h "${user}:${user}" "${home}/node" || true
    # Write upstream-compatible stamp so dashboard boot skips rebuild without npm
    # in a hardened unit PATH. Uses hermes_cli helpers from the pinned checkout.
    sudo -u "${user}" env \
      HERMES_HOME="${home}" \
      PATH="${home}/node/bin:${node_bin}:${PATH}" \
      "${code_dir}/venv/bin/python" - <<'PY'
from hermes_cli.main import PROJECT_ROOT, _web_ui_build_needed, _write_web_ui_build_stamp

web = PROJECT_ROOT / "web"
_write_web_ui_build_stamp(PROJECT_ROOT, web)
if _web_ui_build_needed(web):
    raise SystemExit("web UI stamp still indicates rebuild after write")
PY
    [[ -f "${home}/web-ui-build-stamp.json" ]] || \
      die "missing web-ui-build-stamp.json for profile ${profile}"
    log "dashboard assets ready for profile ${profile}"
  done

  # Never initialize/enable validation-chief here.
  [[ -f "${HERMES_BASE}/profiles/validation-chief/.DISABLED" ]] || \
    die "validation-chief/.DISABLED missing — refuse enabling disabled profile path"
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
  p1="$(grep -E '^HERMES_PORT=' /etc/hermes/jannek-assistant.env | cut -d= -f2 | tr -d '\r')"
  p2="$(grep -E '^HERMES_PORT=' /etc/hermes/cdb-engineer.env | cut -d= -f2 | tr -d '\r')"
  [[ -n "${p1}" && -n "${p2}" && "${p1}" != "${p2}" ]] \
    || die "profile ports must be distinct (got ${p1:-empty} vs ${p2:-empty})"
  log "enabled profile dashboards on ports ${p1} and ${p2}"
}

harden_sudoers_after_bootstrap() {
  local limited="/etc/sudoers.d/99-cdb-hermes"
  cat >"${limited}" <<'EOF'
# Post-bootstrap: service control only — no general root shell (#4289 B2.0).
# Shared hermes may restart dashboards and control only the root-installed cdb-engineer gateway; must NOT start the GitHub token broker or install arbitrary units.
hermes ALL=(root) NOPASSWD: /bin/systemctl start hermes-dashboard@*, /bin/systemctl stop hermes-dashboard@*, /bin/systemctl restart hermes-dashboard@*, /bin/systemctl status hermes-dashboard@*, /bin/systemctl is-active hermes-dashboard@*, /bin/systemctl enable --now hermes-gateway-cdb-engineer.service, /bin/systemctl restart hermes-gateway-cdb-engineer.service, /bin/systemctl status hermes-gateway-cdb-engineer.service, /bin/systemctl is-active hermes-gateway-cdb-engineer.service, /bin/systemctl enable --now hermes-runs-tailnet-transport.service, /bin/systemctl restart hermes-runs-tailnet-transport.service, /bin/systemctl status hermes-runs-tailnet-transport.service, /bin/systemctl is-active hermes-runs-tailnet-transport.service
hermes-jannek-assistant ALL=(root) NOPASSWD: /bin/systemctl status hermes-dashboard@jannek-assistant.service, /bin/systemctl is-active hermes-dashboard@jannek-assistant.service
hermes-cdb-engineer ALL=(root) NOPASSWD: /bin/systemctl status hermes-dashboard@cdb-engineer.service, /bin/systemctl is-active hermes-dashboard@cdb-engineer.service, /bin/systemctl start hermes-github-token.service, /bin/systemctl status hermes-github-token.service
EOF
  chmod 0440 "${limited}"
  if visudo -cf "${limited}" >/dev/null 2>&1; then
    log "sudoers hardened (broker start: hermes-cdb-engineer only)"
  else
    die "sudoers harden failed validation — refuse leaving bootstrap ALL in place without check"
  fi
}

main() {
  [[ "$(id -u)" -eq 0 ]] || die "bootstrap.sh must run as root on the Hetzner host"
  require_cmd rsync
  require_cmd systemctl
  local pin_pair git_ref git_commit
  pin_pair="$(verify_pin)"
  git_ref="${pin_pair%% *}"
  git_commit="${pin_pair##* }"
  ensure_profile_linux_users
  install_systemd_units
  install_profile_env_files
  ensure_profile_homes
  install_hermes_pinned "${git_ref}" "${git_commit}"
  # Re-apply after install: opt tree + uv path exist only post-pin install.
  apply_dedicated_uid_traverse_perms
  ensure_dashboard_runtime_assets
  enable_services
  harden_sudoers_after_bootstrap
  log "bootstrap complete (idempotent re-run safe for homes + units)"
}

main "$@"
