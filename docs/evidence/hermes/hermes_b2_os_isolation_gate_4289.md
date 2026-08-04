# Hermes B2.0 OS isolation evidence (#4289)

Status date: 2026-08-03  
LR: NO-GO  
Gate: `DONE_B2_0_OS_ISOLATION_PASS`

## Repo slice

- Branch: `batch/hermes-github-app-4289`
- PR: `#4332`
- Delivered: per-profile Linux UIDs (`hermes-jannek-assistant` /
  `hermes-cdb-engineer`), systemd `User=hermes-%i`, migrate script (incl.
  parent/opt traverse hardening), broker oneshot contract,
  `HERMES_GH_APP_*` credential separation, unit tests.

## Unit validation

- `pytest -q tests/unit/hermes_ops` → **64 passed** (pre-host-pass baseline)
- `ruff check tools/hermes_ops tests/unit/hermes_ops` → PASS
- `python -m tools.hermes_ops validate-profiles` → ok
- `mint-token --dry-run` → metadata only; `linux_user=hermes-cdb-engineer`
- `secret-scan` → ok

## Live host (`cdb-hermes-01`) — redacted

| Check | Result |
|---|---|
| Exactly one Hermes server | PASS |
| Backups enabled | PASS |
| Rescue path used once (linux64 + verified SSH key) | PASS |
| Host root mounted by UUID (not guessed device) | PASS |
| Hostname / Ubuntu 24.04 | PASS |
| Migrate artifact SHA256 (pre-hardening run) | `8549832719147bd2dc36d0074081358744a4c9e6e2a85c3181988a46ef35aeeb` |
| Rollback pack on host FS (root:root 0700) | PASS |
| Offline identity + unit + ownership apply | PASS |
| Canonical migrate re-run online (idempotent) | PASS (`OS_PROFILE_ISOLATION=PASS`) |
| Dashboard units active + enabled | PASS |
| Process UID jannek-assistant | `hermes-jannek-assistant` (distinct numeric UID) |
| Process UID cdb-engineer | `hermes-cdb-engineer` (distinct numeric UID) |
| Cross-profile home / token-probe / env deny | PASS |
| Profile sudo general denied | PASS |
| validation-chief `.DISABLED` root-owned | PASS |
| Ports loopback-only (`127.0.0.1`) | PASS |
| Memory + sessions present after controlled reboot | PASS |
| Temp FW `/32` removed; inbound rules = 0 | PASS |
| Rescue OFF after cutover | PASS |
| Temp root sudoers removed | PASS |
| PEM / live token dirs | still absent (gate before App) |

## Runtime fixes applied during cutover

- Parent traverse `0751` on `/var/lib/hermes`, `/etc/hermes`, `/var/log/hermes`
  (profiles remain `0700`).
- `/opt/hermes` execute bits for dedicated UIDs (binary tree only).
- `/home/hermes` traverse + uv read path for `ProtectHome=read-only`.
- These are now encoded in `migrate-profile-uids.sh` for future hosts.

## Gate decision

`DONE_B2_0_OS_ISOLATION_PASS`

App creation, PEM transfer, and live token mint are now unblocked for the
already-approved B2 plan. Issue `#4289` remains OPEN. App `4410232` remains
untouched. No secrets, IPs, or key material recorded in this evidence file.

## Non-goals still held until later B2 steps

- No GitHub App created in the B2.0 hop itself
- No PEM transferred in the B2.0 hop itself
- No live installation token in the B2.0 hop itself
- Issue `#4289` remains OPEN
- App `4410232` untouched
