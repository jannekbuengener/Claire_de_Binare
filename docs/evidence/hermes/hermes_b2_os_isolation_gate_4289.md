# Hermes B2.0 OS isolation evidence (#4289)

Status date: 2026-08-03  
LR: NO-GO

## Repo slice

- Branch: `batch/hermes-github-app-4289`
- Base: `origin/main` @ `f2805f47`
- Delivered: per-profile Linux UIDs (`hermes-jannek-assistant` /
  `hermes-cdb-engineer`), systemd `User=hermes-%i`, migrate script, broker
  oneshot contract, `HERMES_GH_APP_*` credential separation, unit tests.

## Unit validation

- `pytest -q tests/unit/hermes_ops` → **64 passed**
- `ruff check tools/hermes_ops tests/unit/hermes_ops` → PASS
- `python -m tools.hermes_ops validate-profiles` → ok
- `mint-token --dry-run` → metadata only; `linux_user=hermes-cdb-engineer`
- `secret-scan` → ok

## Live host (`cdb-hermes-01`)

| Check | Result |
|---|---|
| Dashboards active | PASS |
| Current systemd User | **FAIL / gap** — `User=hermes` for both profiles (pre-migration) |
| Bundle staged under hermes home | PASS (`~/cdb-hermes-bundle-b2`) |
| hermes passwordless root for migrate | **FAIL** — sudo NOPASSWD only for `systemctl` dashboard ops |
| Public TCP/22 from operator network | **FAIL** — timeout despite temporary FW allow `/32` |
| Rescue path | enable-rescue succeeded once; **disabled** without reboot to avoid stranding (public SSH unreachable) |
| Live UID migration | **NOT RUN** |
| Live App create / PEM / token mint | **BLOCKED** by App-creation gate |

## Gate decision

`HOLD_RUNTIME_MIGRATION` / `HOLD_PROFILE_OS_ISOLATION`

App creation, PEM transfer, and live token mint remain forbidden until:

1. Root-capable host session applies `migrate-profile-uids.sh` from the staged
   bundle (or equivalent chroot).
2. Cross-profile negative tests + reboot persistence PASS on the live host.
3. Broker RuntimeDirectory ownership probe PASS.

## Non-goals this slice

- No GitHub App created
- No PEM transferred
- No live installation token
- Issue #4289 remains OPEN
- App `4410232` untouched
