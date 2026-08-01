#!/usr/bin/env bash
# Restore Hermes profile trees from encrypted backup (#4289).
set -euo pipefail

HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes/profiles}"
BACKUP_FILE="${1:-}"
INSTALL_USER="${HERMES_LINUX_USER:-hermes}"

log() { printf '[hermes-restore] %s\n' "$*"; }
die() { printf '[hermes-restore] ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "restore.sh must run as root"
[[ -n "${BACKUP_FILE}" && -f "${BACKUP_FILE}" ]] || die "usage: restore.sh <encrypted-archive>"
[[ "${CONFIRM:-}" == "RESTORE" ]] || die "set CONFIRM=RESTORE"

systemctl stop 'hermes-dashboard@*' 2>/dev/null || true
WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT
ARCHIVE="${WORKDIR}/profiles.tar"

case "${BACKUP_FILE}" in
  *.age)
    command -v age >/dev/null || die "age required"
    age -d -o "${ARCHIVE}" "${BACKUP_FILE}"
    ;;
  *.gpg)
    command -v gpg >/dev/null || die "gpg required"
    gpg --batch --yes -d -o "${ARCHIVE}" "${BACKUP_FILE}"
    ;;
  *)
    die "unsupported archive type (need .age or .gpg)"
    ;;
esac

mkdir -p "${HERMES_BASE}"
tar -C "${HERMES_BASE}" -xf "${ARCHIVE}"
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${HERMES_BASE}"
find "${HERMES_BASE}" -type d -exec chmod 0700 {} \;
systemctl start hermes-dashboard@jannek-assistant.service
systemctl start hermes-dashboard@cdb-engineer.service
systemctl is-active --quiet hermes-dashboard@jannek-assistant.service \
  || die "jannek-assistant failed after restore"
systemctl is-active --quiet hermes-dashboard@cdb-engineer.service \
  || die "cdb-engineer failed after restore"
log "restore complete"
