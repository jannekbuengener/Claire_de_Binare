#!/usr/bin/env bash
# Encrypted off-host backup of Hermes profile data (#4289).
# Excludes .env / PEM / tokens. Requires BACKUP_OUT and AGE_RECIPIENT or GPG_RECIPIENT.
set -euo pipefail

HERMES_BASE="${HERMES_BASE_DIR:-/var/lib/hermes/profiles}"
BACKUP_OUT="${BACKUP_OUT:-}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

log() { printf '[hermes-backup] %s\n' "$*"; }
die() { printf '[hermes-backup] ERROR: %s\n' "$*" >&2; exit 1; }

[[ -n "${BACKUP_OUT}" ]] || die "set BACKUP_OUT to destination directory (off-host)"
[[ -d "${HERMES_BASE}" ]] || die "missing ${HERMES_BASE}"
mkdir -p "${BACKUP_OUT}"

ARCHIVE="${WORKDIR}/hermes-profiles-${STAMP}.tar"
tar --exclude='.env' \
    --exclude='*.pem' \
    --exclude='auth.json' \
    --exclude='*.key' \
    -C "${HERMES_BASE}" \
    -cf "${ARCHIVE}" \
    jannek-assistant cdb-engineer 2>/dev/null || \
  tar --exclude='.env' --exclude='*.pem' --exclude='auth.json' \
    -C "${HERMES_BASE}" -cf "${ARCHIVE}" .

OUT_FILE="${BACKUP_OUT}/hermes-profiles-${STAMP}.tar.age"
if command -v age >/dev/null 2>&1; then
  [[ -n "${AGE_RECIPIENT:-}" ]] || die "set AGE_RECIPIENT for age encryption"
  age -r "${AGE_RECIPIENT}" -o "${OUT_FILE}" "${ARCHIVE}"
elif command -v gpg >/dev/null 2>&1; then
  [[ -n "${GPG_RECIPIENT:-}" ]] || die "set GPG_RECIPIENT for gpg encryption"
  OUT_FILE="${BACKUP_OUT}/hermes-profiles-${STAMP}.tar.gpg"
  gpg --batch --yes -e -r "${GPG_RECIPIENT}" -o "${OUT_FILE}" "${ARCHIVE}"
else
  die "need age or gpg for encrypted backup"
fi

sha256sum "${OUT_FILE}" | tee "${OUT_FILE}.sha256"
log "backup written: ${OUT_FILE}"
