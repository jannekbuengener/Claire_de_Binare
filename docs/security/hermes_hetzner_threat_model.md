# Hermes Hetzner Threat Model

Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)    <!-- pragma: allowlist secret -->
Status: Active  
LR: **NO-GO**

## Assets

| Asset | Sensitivity |
|---|---|
| Hermes profile `.env` / API keys | Critical |
| GitHub App PEM | Critical |
| Profile memories / sessions | High (personal + work) |
| Dedicated Windows workspace | Medium–High |
| CDB repository integrity / merge gates | Critical (must not bypass) |
| Tailscale identity | High |

## Trust boundaries

```text
[Jannek devices]
      |  Tailscale / SSH tunnel + auth
      v
[Hetzner Ubuntu Hermes host]
  - user: hermes (unprivileged)
  - profiles: jannek-assistant | cdb-engineer | (validation-chief disabled)
  - dashboard bind: 127.0.0.1 only (distinct ports per profile)
      | scoped
      +--> [dedicated GitHub App tokens] --> Claire_de_Binare only  <!-- pragma: allowlist secret -->
      +--> [Windows hermes-win via Tailscale Serve → loopback sshd]
             --> D:\Dev\HermesWorkspace\Claire_de_Binare only  <!-- pragma: allowlist secret -->
```

Windows remote path (corrected 2026-08-03): host TCP after Wintun does not
SYN-ACK for peer traffic (`HOLD_WINDOWS_HOST_TCP_STACK`). Remote entry is
**only** private Tailscale Serve TCP → `127.0.0.1:22` (`sshd-hermes`
loopback-only). Funnel forbidden; no public sshd firewall allow.

OS trust boundary: each dashboard runs as a dedicated nologin UID (`hermes-jannek-assistant` / `hermes-cdb-engineer`). Shared `User=hermes` is forbidden for profile processes — `HERMES_HOME` alone is not isolation.

App `4410232` (`cdb-local-ci`) is **not** the Hermes write App unless live
permissions prove `contents`/`pull_requests`/`issues` write without `checks:write`.

## Actors / threats

| Actor | Threat | Mitigation |
|---|---|---|
| Internet anon | Reach Hermes/dashboard | Hetzner firewall deny-inbound; loopback bind; no public 9119/9120 |
| Stolen laptop on Tailscale | Abuse Hermes | Hermes auth for non-loopback; OS login; approvals.deny; redact_secrets |
| Prompt injection via tools | Escape workspace | Docker/SSH allowlists; deny rules; no YOLO in units |
| Compromised cdb-engineer | Broad GitHub admin | Scoped installation tokens; forbid checks:write / admin merge / secrets |
| Cross-profile bleed | Personal ↔ engineering secrets | Separate HERMES_HOME; 0700 dirs; no shared omnipotent profile |
| Windows lateral movement | Read personal profile / browser | Dedicated user + NTFS allowlist; kill-switch |
| Supply-chain install | Malicious install.sh | VERSION_PIN sha256 + git_ref; refuse unpinned curl\|bash |
| Backup leakage | Secrets in archives | Encrypt off-host backups; exclude PEM from agent paths |
| Authority confusion | Live/merge claims | Policy + SOUL/AGENTS hard denies; LR SSOT unchanged |

## Kill-switch

| Switch | Effect |
|---|---|
| Windows `kill-switch.ps1 -Action Disable` | Serve TCP mapping off + `sshd-hermes` stopped/disabled → `WORKSTATION_UNAVAILABLE` |
| Stop Tailscale on Windows or Hetzner | Private path gone; no public fallback |
| `systemctl stop 'hermes-dashboard@*'` | Agent offline |
| Revoke GitHub App installation / rotate PEM | Tokens useless |
| `CONFIRM=DESTROY destroy.sh` | Cloud resources removed |

Stopped bridge ⇒ unavailable, **never** silent fallback to public SSH/RDP.

## Forbidden capability combinations

A single profile MUST NOT combine:

- personal memory lane **and**
- Windows admin **or** GitHub admin **or** CDB live authority

Enforced in `tools/hermes_ops/policy.py` (`omnipotent_combination_forbidden`).

## Auth lineage

Token minting reuses JWT/PEM helpers from `ci.publisher.app_auth` (#4170 / #4195)
as library code only. Hermes adds repository + permission scoping, rejects App
`4410232` without a verified compatible permission map, forbids `checks:write`,
and writes live tokens only to a `0600` `--token-file` (never stdout).

## Residual risks

- Operator mis-pinning a bad Hermes release (process control / code review).
- Tailscale ACL mistakes (document least privilege separately).
- Model provider account compromise (keys in `/etc/hermes`, not repo).
- #4270 validation-chief activation without contract (kept `.DISABLED`).

## References

- [Hermes Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)
- [Hermes Web Dashboard auth gate](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard)
- [Hetzner Firewalls](https://docs.hetzner.com/cloud/firewalls/faq/)
- [GitHub App installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
