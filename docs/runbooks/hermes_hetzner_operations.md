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

## Preconditions

1. Hetzner Cloud API token available to the **operator** (not committed).
2. `hcloud` CLI authenticated.
3. Tailscale (or equivalent private net) planned for Jannek ↔ Hetzner ↔ Windows.
4. `infrastructure/hermes/VERSION_PIN.yaml` filled with Hermes `git_ref` and
   `install_script_sha256` before install.
5. GitHub App credentials reuse lineage [#4170](https://github.com/jannekbuengener/Claire_de_Binare/issues/4170) /  <!-- pragma: allowlist secret -->
   [#4195](https://github.com/jannekbuengener/Claire_de_Binare/issues/4195) when compatible.  <!-- pragma: allowlist secret -->
   PEM path **outside** `/var/lib/hermes/profiles` and `D:\Dev\HermesWorkspace`.

## Repo validation (no cloud credentials)

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check --profile cdb-engineer --action github_write_branch_pr --expect allow
python -m tools.hermes_ops policy-check --profile jannek-assistant --action windows_shell --expect deny
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run
python -m tools.hermes_ops pin-check
```

## Provision (Hetzner)

```bash
# 1) Create firewall from infrastructure/hermes/hetzner/firewall.yaml intent
# 2) Create server from server.yaml + cloud-init.yaml (inject SSH pubkey)
# 3) Attach firewall / labels role=hermes
# 4) Join Tailscale; remove any temporary public SSH exception
# 5) On host, as root:
sudo bash infrastructure/hermes/hetzner/bootstrap.sh
```

Bootstrap is idempotent for profile homes and systemd units. It **STOPS** if the
version pin is empty or `install.sh` sha256 mismatches.

## Profiles

| Profile | Enable | Windows | GitHub write |
|---|---|---|---|
| `jannek-assistant` | yes | no | no |
| `cdb-engineer` | yes | dedicated workspace | scoped App token |
| `validation-chief` | **no** (`.DISABLED`) until #4270 | no | no |

Each profile has its own `HERMES_HOME` under `/var/lib/hermes/profiles/<name>/`.

## Start / Stop / Status

```bash
sudo systemctl start hermes-serve@jannek-assistant
sudo systemctl start hermes-serve@cdb-engineer
sudo systemctl status 'hermes-serve@*'
sudo -u hermes HERMES_HOME=/var/lib/hermes/profiles/cdb-engineer /opt/hermes/bin/hermes doctor
```

`hermes serve` binds `127.0.0.1:9119` only. Reach it via Tailscale SSH tunnel or
loopback on the host. Non-loopback binds require Hermes auth providers; `--insecure`
must not be used (unit forbids it).

## GitHub token mint

```bash
# Preview (no credentials required)
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run

# Live mint on the host with App env configured (token opt-in print)
python -m tools.hermes_ops mint-token --profile cdb-engineer --print-token
```

Forbidden for all Hermes profiles: `cdb-local-ci` publish, admin merge,
branch-protection edits, secret read/write, force-push, default-branch delete,
App permission expansion.

## Windows workspace

On Windows (Human-GO, elevated once):

```powershell
.\infrastructure\hermes\windows\setup-workspace.ps1 -HermesUser hermes-win
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Status
```

Kill-switch:

```powershell
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Disable   # WORKSTATION_UNAVAILABLE
.\infrastructure\hermes\windows\kill-switch.ps1 -Action Enable
```

No public SSH/RDP/VNC. OpenSSH only on private net for `hermes-win`.

## Backup / Restore

1. Enable Hetzner server backups (`server.yaml` → `backups: true`).
2. Additionally: encrypted off-host archive of `/var/lib/hermes/profiles/*/memories`,
   `sessions`, `config.yaml`, `SOUL.md`, skills — **exclude** `.env` from unencrypted
   channels; store secrets via operator secret store.
3. Restore: stop units → restore profile trees with `0700` → start units → `hermes doctor`.

## Update / Rollback

1. Set new pin in `VERSION_PIN.yaml` (ref + sha256).
2. Drain sessions; `systemctl stop 'hermes-serve@*'`.
3. Re-run pinned install path from bootstrap (or documented update procedure).
4. `hermes doctor` per profile; start units.
5. Rollback: re-pin previous ref/sha256 and reinstall; restore profile data from backup.

## Rotation / Revoke

- Rotate GitHub App PEM offline; update `/etc/hermes/*.env` paths only.
- Revoke outstanding installation tokens by rotating the App private key / suspending installation.
- Tailscale: remove device key for host and Windows node as needed.
- Windows: kill-switch Disable + disable `hermes-win` login.

## Destroy

```bash
CONFIRM=DESTROY bash infrastructure/hermes/hetzner/destroy.sh
```

Then complete the revocation checklist printed by the script.

## Evidence

Repo-side evidence template:
`docs/evidence/hermes/hermes_hetzner_repo_slice_evidence.md`

Live E2E evidence (portscan, reboot persistence, backup drill, Windows ACL drill)
stays **outside** the repository when it contains host inventory. Redact secrets/PII.

## Non-goals reminder

No public dashboard, no K8s, no GUI automation, no personal memory in git,
no second GitHub App authenticator, no merge-gate bypass, no live trading.
