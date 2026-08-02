# Hermes Hetzner Operations Runbook

Status: Active operator runbook
Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)    <!-- pragma: allowlist secret -->
LR: **NO-GO** (unchanged)
Board stage: `trade-capable` ≠ Live-Go

## Purpose

Operate a single Ubuntu LTS Hermes host on Hetzner with segmented profiles,
private remote access, scoped GitHub App tokens, and a dedicated Windows
workspace — without public dashboards or omnipotent agents.

## Surfaces

| Path | Role |
|---|---|
| `infrastructure/hermes/` | Provision, systemd, Windows scripts, version pin |
| `config/hermes/profiles/` | Versioned profile distributions (no secrets) |
| `tools/hermes_ops/` | Validate, secret-scan, policy, token broker |
| `docs/security/hermes_hetzner_threat_model.md` | Trust boundaries + kill-switch |

## Official docs (pin sources)

- Installation: https://hermes-agent.nousresearch.com/docs/getting-started/installation
- Web Dashboard flags: https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard
- CLI reference: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- Release tag used in pin: `v2026.7.30` (Hermes Agent v0.19.1)

Entrypoint: **`hermes dashboard`** (not `hermes serve` for the web UI).
Installer env `HERMES_GIT_REF` is **not** supported; use `--branch` / `--commit`.

## Preconditions

1. Valid **Hetzner Cloud** API token for `hcloud` (operator-owned; not in repo).
   - Object Storage Access/Secret keys (`HETZNER_ACCESS_KEY` / `HETZNER_SECRET_KEY`
     shape) are a **different product** and do **not** authorize `hcloud`.
   - Do not set `HCLOUD_TOKEN` from Object Storage credentials.
2. `hcloud` CLI authenticated (`hcloud server list` succeeds).
3. Tailscale (or equivalent private net) for Jannek ↔ Hetzner ↔ Windows.
4. `infrastructure/hermes/VERSION_PIN.yaml` filled; `python -m tools.hermes_ops pin-check --require-pinned` exits 0.
5. Dedicated GitHub App for Hermes write with minimal perms (see below).
   **Do not** expand App `4410232` (`cdb-local-ci`: `checks:write` + `metadata:read` only).
   Auth lineage [#4170](https://github.com/jannekbuengener/Claire_de_Binare/issues/4170) /  <!-- pragma: allowlist secret -->
   [#4195](https://github.com/jannekbuengener/Claire_de_Binare/issues/4195) is reference-only unless a separate App proves compatible perms.  <!-- pragma: allowlist secret -->
6. PEM path **outside** `/var/lib/hermes/profiles` and `D:\Dev\HermesWorkspace`.

## Repo validation (no cloud credentials)

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check --profile cdb-engineer --action github_write_branch_pr --expect allow
python -m tools.hermes_ops policy-check --profile jannek-assistant --action windows_shell --expect deny
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run
python -m tools.hermes_ops pin-check --require-pinned
pytest -q tests/unit/hermes_ops
ruff check tools/hermes_ops tests/unit/hermes_ops
```

## Provision (Hetzner)

Cost gate: CX23 + IPv4 + backups ≈ **9.03 EUR/mo** (live price table 2026-08-02) &lt; 15 EUR.
(`cpx21` remains documented as legacy intent but is no longer orderable in EU locations.)

```bash
export HCLOUD_TOKEN="$(tr -d '\r\n' < \"$HOME/Documents/.secrets/.cdb/HCLOUD_TOKEN.txt\")"
export HERMES_SSH_KEY_NAME=cdb-hermes-hetzner
# Optional short-lived admin SSH during first bootstrap (remove after Tailscale):
export HERMES_BOOTSTRAP_ADMIN_CIDR=<your-public-ip>/32
bash infrastructure/hermes/hetzner/provision.sh
# On host, after Tailscale is up and any temporary public SSH exception removed:
sudo bash infrastructure/hermes/hetzner/bootstrap.sh
```

`provision.sh` is idempotent (no duplicate `cdb-hermes-01`).
`bootstrap.sh` fails closed on empty pin, sha256 mismatch, or service start errors (no `|| true`).

Ports (loopback only):

| Profile | Port |
|---|---|
| `jannek-assistant` | 9119 |
| `cdb-engineer` | 9120 |
| `validation-chief` | 9121 (disabled) |

## Profiles

| Profile | Enable | Windows | GitHub write |
|---|---|---|---|
| `jannek-assistant` | yes | no | no |
| `cdb-engineer` | yes | dedicated workspace | scoped App token |
| `validation-chief` | **no** (`.DISABLED`) until #4270 | no | no |

Each profile has its own `HERMES_HOME` under `/var/lib/hermes/profiles/<name>/`.

## Start / Stop / Status

```bash
sudo systemctl start hermes-dashboard@jannek-assistant
sudo systemctl start hermes-dashboard@cdb-engineer
sudo systemctl status 'hermes-dashboard@*'
sudo -u hermes HERMES_HOME=/var/lib/hermes/profiles/cdb-engineer /opt/hermes/bin/hermes doctor
```

Unit binds `127.0.0.1:${HERMES_PORT}` with `--no-open --isolated`. Reach via Tailscale
SSH tunnel or host loopback. Non-loopback binds require Hermes auth providers;
`--insecure` is a no-op and must not be used as a security control.

## GitHub token mint

Minimal dedicated App permission set (repo `jannekbuengener/Claire_de_Binare` only):

- `contents: write`
- `pull_requests: write`
- `issues: write`
- `metadata: read`
- **no** `checks: write`

```bash
# Preview (no credentials / no token)
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run

# Live mint — token ONLY to a 0600 file (never stdout)
python -m tools.hermes_ops mint-token --profile cdb-engineer \
  --token-file /run/hermes/cdb-engineer.token
```

Forbidden: `cdb-local-ci` publish, admin merge, branch-protection edits,
secret read/write, force-push, default-branch delete, App permission expansion.

## Windows workspace

On Windows (elevated once / UAC):

```powershell
# Prefer SecureString; HERMES_WIN_PASSWORD env is accepted then cleared
.\infrastructure\hermes\windows\setup-workspace.ps1 -HermesUser hermes-win -GrantWrite
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Status
```

Kill-switch:

```powershell
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Disable   # WORKSTATION_UNAVAILABLE
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Enable
```

No public SSH/RDP/VNC. OpenSSH only on private net for `hermes-win`.

## Backup / Restore / Update / Rollback

```bash
BACKUP_OUT=/mnt/offhost AGE_RECIPIENT=<age-pubkey> \
  bash infrastructure/hermes/hetzner/backup.sh

CONFIRM=RESTORE bash infrastructure/hermes/hetzner/restore.sh /mnt/offhost/hermes-profiles-*.tar.age

# Reads install_url + sha256 + commit from VERSION_PIN.yaml (required).
# Checkout path: /opt/hermes/hermes-agent (same as bootstrap.sh).
CONFIRM=UPDATE bash infrastructure/hermes/hetzner/update.sh

CONFIRM=ROLLBACK bash infrastructure/hermes/hetzner/rollback.sh
```

`update.sh` / `rollback.sh` refuse unsigned `main/scripts/install.sh` downloads
and fail if pin sha256 is empty or mismatched.

Hetzner server backups are required: `provision.sh` enables them or dies
(`server.yaml` → `backups: true` is the intent mirror).

## Rotation / Revoke

- Rotate GitHub App PEM offline; update `/etc/hermes/*.env` paths only.
- Revoke outstanding installation tokens by rotating the App private key / suspending installation.
- Tailscale: remove device key for host and Windows node as needed.
- Windows: kill-switch Disable + disable `hermes-win` login.

## Destroy

```bash
CONFIRM=DESTROY bash infrastructure/hermes/hetzner/destroy.sh
```

Only `cdb-hermes-01` + `cdb-hermes-deny-inbound` are eligible, and the server
must carry labels `role=hermes`, `issue=4289`, `project=claire-de-binare`.
Name-only matches without those labels are refused. Then complete the
revocation checklist printed by the script.

## Evidence

Repo-side evidence:
`docs/evidence/hermes/hermes_hetzner_repo_slice_evidence.md`

Live E2E evidence (portscan, reboot persistence, backup drill, Windows ACL drill)
stays **outside** the repository when it contains host inventory. Redact secrets/PII.

## Non-goals reminder

No public dashboard, no K8s, no GUI automation, no personal memory in git,
no silent expansion of `cdb-local-ci` App, no merge-gate bypass, no live trading.
