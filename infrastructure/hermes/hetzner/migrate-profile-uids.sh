#!/usr/bin/env bash
# Migrate Hermes host from shared User=hermes dashboards to per-profile UIDs (#4289 B2.0).
# Fail-closed. Does NOT create GitHub Apps, transfer PEMs, or mint tokens.
set -euo pipefail

log() { printf '[hermes-uid-migrate] %s\n' "$*"; }
die() {
  printf '[hermes-uid-migrate] ERROR: %s\n' "$*" >&2
  printf '[hermes-uid-migrate] HOLD_PROFILE_OS_ISOLATION\n' >&2
  exit 2
}

[[ "$(id -u)" -eq 0 ]] || die "must run as root on cdb-hermes-01"

HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes}"
LOG_BASE="${HERMES_LOG_DIR:-/var/log/hermes}"
SYSTEMD_SRC="${HERMES_SYSTEMD_SRC:-/opt/cdb-hermes-bundle/infrastructure/hermes/systemd}"
BACKUP_DIR="${HERMES_UID_MIGRATE_BACKUP:-/var/backups/hermes-uid-migrate-$(date -u +%Y%m%dT%H%M%SZ)}"

declare -A PROFILE_USERS=(
  [jannek-assistant]=hermes-jannek-assistant
  [cdb-engineer]=hermes-cdb-engineer
)

ensure_nologin_user() {
  local user="$1"
  if id -u "${user}" >/dev/null 2>&1; then
    local shell
    shell="$(getent passwd "${user}" | awk -F: '{print $7}')"
    case "${shell}" in
      */nologin|*/false) ;;
      *) die "user ${user} has login shell ${shell} — refuse (require nologin)" ;;
    esac
    log "user present: ${user}"
    return
  fi
  useradd --system --user-group --create-home=no --shell /usr/sbin/nologin "${user}" \
    || die "useradd failed for ${user}"
  log "created system user ${user}"
}

backup_runtime() {
  mkdir -p "${BACKUP_DIR}"
  chmod 0700 "${BACKUP_DIR}"
  systemctl stop 'hermes-dashboard@*' 2>/dev/null || true
  if [[ -d "${HERMES_BASE}/profiles" ]]; then
    tar -C "${HERMES_BASE}" -cf "${BACKUP_DIR}/profiles.tar" profiles
    log "backed up profiles to ${BACKUP_DIR}/profiles.tar"
  fi
  # Capture unit identity evidence before cutover.
  systemctl show hermes-dashboard@jannek-assistant.service -p User -p Group \
    >"${BACKUP_DIR}/unit-jannek-assistant.before" 2>/dev/null || true
  systemctl show hermes-dashboard@cdb-engineer.service -p User -p Group \
    >"${BACKUP_DIR}/unit-cdb-engineer.before" 2>/dev/null || true
}

install_units() {
  local dash="${SYSTEMD_SRC}/hermes-dashboard@.service"
  local broker="${SYSTEMD_SRC}/hermes-github-token.service"
  if [[ ! -f "${dash}" ]]; then
    # Fallback: units already under /etc when re-running from host copy.
    dash="/etc/systemd/system/hermes-dashboard@.service"
  fi
  [[ -f "${dash}" ]] || die "missing dashboard unit source (${SYSTEMD_SRC})"
  install -m 0644 "${dash}" /etc/systemd/system/hermes-dashboard@.service
  if [[ -f "${broker}" ]]; then
    install -m 0644 "${broker}" /etc/systemd/system/hermes-github-token.service
  elif [[ -f /etc/systemd/system/hermes-github-token.service ]]; then
    log "broker unit already installed"
  else
    log "broker unit not yet present in bundle — dashboard isolation proceeds"
  fi
  systemctl daemon-reload
}

migrate_ownership() {
  local profile user home logdir
  mkdir -p "${LOG_BASE}"
  chmod 0751 "${LOG_BASE}"
  for profile in jannek-assistant cdb-engineer; do
    user="${PROFILE_USERS[${profile}]}"
    ensure_nologin_user "${user}"
    home="${HERMES_BASE}/profiles/${profile}"
    logdir="${LOG_BASE}/${profile}"
    [[ -d "${home}" ]] || die "missing profile home ${home}"
    mkdir -p "${logdir}"
    chown -R "${user}:${user}" "${home}"
    chmod 0700 "${home}"
    chmod 0700 "${home}/memories" "${home}/sessions" "${home}/logs" 2>/dev/null || true
    chown -R "${user}:${user}" "${logdir}"
    chmod 0700 "${logdir}"
    # Env files: root-owned, readable by profile group only (no shared hermes group).
    if [[ -f "/etc/hermes/${profile}.env" ]]; then
      chown "root:${user}" "/etc/hermes/${profile}.env"
      chmod 0640 "/etc/hermes/${profile}.env"
    fi
    log "ownership migrated: ${profile} -> ${user}"
  done
  # validation-chief stays disabled; root-owned sentinel, not engineer/assistant readable secrets.
  if [[ -d "${HERMES_BASE}/profiles/validation-chief" ]]; then
    chmod 0700 "${HERMES_BASE}/profiles/validation-chief"
    touch "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
    chown root:root "${HERMES_BASE}/profiles/validation-chief" \
      "${HERMES_BASE}/profiles/validation-chief/.DISABLED"
  fi
  # Shared install tree may remain under hermes (binary only — no tokens/PEM).
  if id -u hermes >/dev/null 2>&1 && [[ -d /opt/hermes ]]; then
    chown -R hermes:hermes /opt/hermes
  fi
}

verify_unit_identities() {
  local profile user got_user
  for profile in jannek-assistant cdb-engineer; do
    user="${PROFILE_USERS[${profile}]}"
    got_user="$(systemctl show "hermes-dashboard@${profile}.service" -p User --value)"
    [[ "${got_user}" == "${user}" ]] \
      || die "dashboard@${profile} User=${got_user} expected ${user}"
  done
}

start_and_probe() {
  systemctl enable hermes-dashboard@jannek-assistant.service
  systemctl enable hermes-dashboard@cdb-engineer.service
  systemctl restart hermes-dashboard@jannek-assistant.service
  systemctl restart hermes-dashboard@cdb-engineer.service
  systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
    || die "jannek-assistant dashboard failed after UID migration"
  systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
    || die "cdb-engineer dashboard failed after UID migration"
  verify_unit_identities
}

negative_cross_profile() {
  local ja=hermes-jannek-assistant
  local eng=hermes-cdb-engineer
  local eng_home="${HERMES_BASE}/profiles/cdb-engineer"
  local ja_home="${HERMES_BASE}/profiles/jannek-assistant"
  # Engineer home must be unreadable by assistant.
  if sudo -u "${ja}" test -r "${eng_home}/config.yaml" 2>/dev/null; then
    die "jannek-assistant can read cdb-engineer home — HOLD_PROFILE_OS_ISOLATION"
  fi
  if sudo -u "${eng}" test -r "${ja_home}/config.yaml" 2>/dev/null; then
    die "cdb-engineer can read jannek-assistant home — HOLD_PROFILE_OS_ISOLATION"
  fi
  # Simulated token dir: only engineer may read after we create a probe file as root.
  local probe_dir="/run/hermes/cdb-engineer"
  mkdir -p "${probe_dir}"
  echo "PROBE_NOT_A_REAL_TOKEN" >"${probe_dir}/token"
  chown "${eng}:${eng}" "${probe_dir}" "${probe_dir}/token"
  chmod 0700 "${probe_dir}"
  chmod 0600 "${probe_dir}/token"
  if sudo -u "${ja}" test -r "${probe_dir}/token" 2>/dev/null; then
    rm -f "${probe_dir}/token"
    die "jannek-assistant can read engineer token path — HOLD_TOKEN_DELIVERY_ISOLATION"
  fi
  if sudo -u hermes test -r "${probe_dir}/token" 2>/dev/null; then
    rm -f "${probe_dir}/token"
    die "shared hermes user can read engineer token path — HOLD_TOKEN_DELIVERY_ISOLATION"
  fi
  sudo -u "${eng}" test -r "${probe_dir}/token" \
    || die "cdb-engineer cannot read own token probe — HOLD_TOKEN_DELIVERY_ISOLATION"
  rm -f "${probe_dir}/token"
  # PEM path must not exist yet OR must be root-only (no profile read).
  if [[ -f /etc/hermes/secrets/cdb-hermes-engineer.pem ]]; then
    if sudo -u "${eng}" test -r /etc/hermes/secrets/cdb-hermes-engineer.pem 2>/dev/null; then
      die "cdb-engineer can read PEM — HOLD_TOKEN_DELIVERY_ISOLATION"
    fi
    if sudo -u "${ja}" test -r /etc/hermes/secrets/cdb-hermes-engineer.pem 2>/dev/null; then
      die "jannek-assistant can read PEM — HOLD_TOKEN_DELIVERY_ISOLATION"
    fi
  fi
  # Assistant must not be able to start the broker unit.
  if sudo -u "${ja}" systemctl start hermes-github-token.service 2>/dev/null; then
    systemctl stop hermes-github-token.service 2>/dev/null || true
    die "jannek-assistant started broker unit — HOLD_TOKEN_DELIVERY_ISOLATION"
  fi
  log "cross-profile negative controls PASS"
}

main() {
  log "starting UID migration (no GitHub App / no PEM transfer / no live mint)"
  backup_runtime
  for profile in jannek-assistant cdb-engineer; do
    ensure_nologin_user "${PROFILE_USERS[${profile}]}"
  done
  install_units
  migrate_ownership
  start_and_probe
  negative_cross_profile
  log "OS_PROFILE_ISOLATION=PASS TOKEN_DELIVERY_PROBE=PASS"
  log "next: controlled reboot + persistence proof, then App-creation gate"
}

main "$@"
